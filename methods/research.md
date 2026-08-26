# How this run works

## Submitting work

`submit_job` sends work to a remote compute system through Globus Compute and returns a
`job_id`. The system is selected by configuration; you do not name it.

`get_completed_jobs` collects whatever has finished. Call it near the start of a turn.

After submitting, end your turn. Jobs keep running and you are resumed when they finish.

Check `results.jsonl` and jobs in flight before submitting, so each configuration runs
once.

Resource values — endpoint, account, queue, node count, walltime, concurrency — live in
`config.json` and are authoritative. Read them there when a value matters.

## Results carry diagnostics

Each result includes a `diagnostics` block parsed from the job's own output, and a path
to its full log. Read it in full on your first result and skim it on each one after.
What it reports often locates a problem faster than another run will.

## Work in cycles

A cycle spans several turns: you submit, end your turn, and resume when jobs finish.
Keep a cycle open until you have interpreted its data, then write it up and open the
next. Each cycle builds on the conclusion of the last, so a reader can follow what you
are pursuing and why.

1. **Observe.** What is known going in — data so far, the last cycle's conclusion.
2. **Hypothesize.** One concrete, falsifiable statement, naming the mechanism you think
   is responsible.
3. **Predict.** Write down what each planned job will show if the hypothesis holds, and
   what result would refute it, before you submit.
4. **Experiment.** Submit. Vary one thing per job, so a difference is attributable.
5. **Interpret.** What the data says.

Keep each step to a short block. A refuted hypothesis is a good cycle.

## Records

All in the shared area.

- **`results.jsonl`** — one JSON object per line, appended as each result lands. Correct
  an entry by appending a new line describing the change.
- **`LOGBOOK.md`** — your memory across runs, append-only, terse. What you tried, what it
  showed, what you concluded, which lines of enquiry are closed. You start each run with
  no memory of the last one, so anything not written here is lost. One line per cycle
  pointing at its journal section; the write-up itself goes in the journal.
- **`JOURNAL.md`** — the readable record. Append a section per cycle: the five steps, the
  figures with captions, and pointers to the `results.jsonl` lines behind each claim.
- **`JOURNAL.tex`** — the same record as one accumulating LaTeX document, so the run has
  a typeset report at any point.

Write the journal entry when a cycle's experiment finishes, not at the end of the run.

At the end of a run, append a closing summary to `LOGBOOK.md`: the outcome, what
explains it, what was eliminated, and what is worth trying next.

### When there is a lot to read

Where there is a lot to read, ask a subagent to read it and answer, if one is
available. The `reader` subagent is set up for that; its call blocks, so the answer
arrives in the same turn.

## Figures

A figure is an image file, not a description of one. Plot with matplotlib through `Bash`,
save under `journal/figures/` in the shared area, and reference it from both journal
files with a brief caption saying what it shows. Keep the plotting script beside its
figure so it can be redrawn when more data lands.

## The LaTeX journal

Create `JOURNAL.tex` on your first cycle if it does not exist, with this preamble:

```latex
\documentclass[11pt,a4paper]{article}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage[margin=1in]{geometry}
\usepackage{hyperref}
\graphicspath{{journal/figures/}}
\title{<campaign name>}
\date{\today}
\begin{document}
\maketitle
\end{document}
```

Then append one `\section` per cycle immediately before `\end{document}`, mirroring the
`JOURNAL.md` entry and using `\includegraphics` for its figures. Never rewrite an earlier
section, and never touch the preamble after creating it.

It must stay compilable. Run `pdflatex -interaction=nonstopmode JOURNAL.tex` in the
shared area after each append, and fix any error before continuing — a journal that no
longer builds is the one thing here you cannot leave for later. If `pdflatex` is not
installed, say so once in `LOGBOOK.md` and keep `JOURNAL.tex` correct anyway.

## Failures

Re-run work whose data is broken.

A job that fails identically across attempts is an infrastructure problem. Record it and
move on.

For something you cannot work around — the endpoint is unreachable and submissions keep
failing — call `notify` with `blocking=true` and one line saying what is wrong.

## Ending

You will be told explicitly if a wind-down is requested. Then submit no new work,
collect what is in flight, and write up where you got to.
