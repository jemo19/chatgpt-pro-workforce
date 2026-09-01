# Research explorer

The research explorer is the file you open when you want to read the result,
not the machinery behind it.

It is built after Codex accepts the research. The page keeps the summary,
findings, source links, confidence, contradictions, limitations,
recommendations, and artifact list in one place. Search and filters work inside
the file, so it does not need a web server or internet connection.

## Choose when it is made

The first-run walkthrough offers three choices:

- Always build one after an accepted research run. This is the recommended
  setting.
- Ask when the run reaches the final handoff.
- Leave it off.

Change the setting later by asking the skill to change its research explorer
preference. For one accepted run, use:

```text
$chatgpt-pro-workforce export explorer RUN_ID
```

If the research has not passed its checks, the skill reports what is missing.
It does not make a provisional page that looks final.

## Where the file goes

The first verified copy stays in that run's `accepted` folder. If setup points
at a final Downloads folder or another output folder, the skill copies those
same verified bytes to one explicit filename and checks both hashes.

A normal name looks like this:

```text
topic-name-research-explorer-RUN-YYYYMMDD-NNN.html
```

The skill does not treat the rest of Downloads as its property and does not
clean unrelated files.

## What works offline

- Search findings and sources.
- Filter by topic, confidence, and evidence state.
- Move from a finding to the sources that support it.
- See contradictions and limitations beside the relevant result.
- Sort the source register.
- Expand detail without losing the short reading path.
- Print a clean report.

The file contains its own styles, scripts, and accepted data. It does not load
fonts, libraries, images, analytics, or data from another site. Source links are
ordinary links and open only when you choose them.

If JavaScript is blocked, the interactive filters disappear but the research
itself remains readable.

## What it does not replace

The explorer is the reading copy. Raw worker returns, accepted native files,
source notes, hashes, and validation records remain the evidence. If the page
does not agree with that evidence, the page fails review; the presentation does
not get to change the research.
