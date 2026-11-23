# AI Disclosure

I acknowledge the use of Claude (Anthropic, https://claude.ai) to plan, write,
explain and test this project. Most of the code was written by the AI; I made
the design decisions, wrote part of the validation layer, ran and checked every
module, and rejected or changed suggestions that did not fit the course.

## How AI was used, file by file

| File | Who wrote it | My part |
| --- | --- | --- |
| `models.py` | AI | Rejected the first version (it used `@dataclass`, not covered in class) and asked for a hand-written class; chose to keep `date` as text |
| `validation.py` | Mixed | I wrote `validate_kind` and `validate_category` following the pattern of `validate_amount`; the AI reviewed them and found a bug in my first `validate_kind` (non-text input crashed with `UnboundLocalError` instead of a clear `ValueError`). The AI wrote `validate_amount`, `validate_currency`, `validate_date`, `validate_id`, `validate_month` and `parse_record`, explaining each step |
| `services.py` | AI | Asked how income is recorded and decided not to cross-check category and kind |
| `storage.py` | AI | Reviewed the safe-write and backup logic against the File I/O session notebook |
| `cli.py`, `__main__.py` | AI | Asked for an interactive mode after we noticed the syllabus requires entering several transactions without restarting the program |
| `tests/` | AI | Ran all tests; the AI also broke the code on purpose to show each test can fail |
| `README.md`, `DESIGN.md` | AI, from my decisions | Checked that they describe the code as it is |
| Project setup (uv, WSL, Git) | Me, guided by AI | Fixed the missing `[project.scripts]` entry with the AI's help |

## Decisions that were mine

- JSON instead of CSV for storage (the AI recommended CSV).
- No `@dataclass`, because we have not covered it in class.
- Two interfaces: command mode and interactive mode.
- Not checking that a category matches its kind (accepted as a known limitation).
- Not committing the real data file.

## Prompts used (summarized)

- "Let's continue the budget-manager project" / "let's do models, validation,
  services, storage, cli" (one module at a time).
- "Let's do validate_amount first so I can see how it is and extrapolate to the
  others", then I wrote the next validators and asked for a review.
- Concept questions: why the class has no `self` parameters with `@dataclass`,
  what `{value!r}` does, whether `1` or `0` would be rejected, where `argparse`
  and `input()` act, where the data is stored, what happens with income.
- "Let's clarify what the project is about for the README", "complete the
  README", "give me the design document".

## How I checked the output

- Ran each module in the terminal before committing it (`uv run python -c ...`
  and the `budget` commands with a test data file).
- Ran the full test suite with `uv run pytest`.
- Compared the requirements with the syllabus (Session 10) and the course
  slides; this is how the missing interactive loop was detected.
- Asked for explanations of every part I did not understand, so I can explain
  each design decision myself.

## What I would not trust without checking

The AI produced working code quickly, but its first proposals did not always
fit the course: it used tools we have not seen (`@dataclass`) and its first
plan only had command mode, which did not meet the "multiple entries without
restarting" requirement. AI output needed to be checked against the course
requirements, not just against whether it runs.