# How this run works

A short run, meant to be read. Do the work in a few jobs and say what you found in a
few lines — someone should be able to open `LOGBOOK.md` and see what happened without
reading a report.

## Submitting work

`submit_job` sends work to a remote compute system through Globus Compute and returns a
`job_id`; `submit_local` runs a job on this machine. Either returns immediately.

`get_completed_jobs` (or `get_local_completed`) collects whatever has finished. Call it
near the start of a turn.

Submit everything a step needs at once, then end your turn. Jobs run while you are away
and you are resumed when they finish. Submitting one job per turn wastes most of the
run's time waiting for you rather than for the work.

## Work in cycles

A cycle is: decide what to find out, submit the jobs that would settle it, read what
came back.

1. **Ask.** One thing you want to know, and what result would answer it.
2. **Submit.** All the jobs that bear on it, in one go.
3. **Read.** What the results say, and whether they answered it.
4. **Close.** Add the cycle to `LOGBOOK.md`, then call `cycle_done` with what it
   established, before opening the next one.

If the answer turns out to be no, that is a finished cycle, not a failed one.

## Records

- **`results.jsonl`** — one JSON object per line, appended as each result lands. Every
  number you rely on lives here; a number that exists only in prose cannot be checked.
- **`LOGBOOK.md`** — a few lines per cycle: what you asked, what came back, what you
  concluded. You start each run with no memory of the last one, so what is not written
  here is lost.

Keep it short. A cycle entry is a handful of lines, not a section.

## The write-up

`JOURNAL.md` is what someone reads when the run is over: a section per cycle, in order,
saying what you asked, what came back and what you concluded. Where a plot shows
something the numbers do not, make one with matplotlib through `Bash`, save it beside
the journal and reference it there with a caption. Keep the section to a few
paragraphs; `LOGBOOK.md` holds the running notes and `results.jsonl` holds the numbers.

## Claims

Say what the results show and no more. Where you are reasoning past them — a shape you
are inferring, a cause you are proposing, a number from outside the run — say that in
the same sentence. "Probably X, on two readings" is worth more than a confident X.

## Failures

Re-run work whose data is broken. A job that fails the same way every time is an
infrastructure problem: record it and move on.

For something you cannot work around, call `notify` with `blocking=true` and one line
saying what is wrong.

## Ending

You will be told explicitly if a wind-down is requested. Then submit no new work,
collect what is in flight, and add a closing entry: what you found, and what you would
do next with more jobs.
