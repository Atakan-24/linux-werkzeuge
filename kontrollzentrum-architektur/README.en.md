# Security-assessment control center: architecture and design decisions

A local desktop application (Python, Tkinter) that guides beginners through security assessments:
from the target, through written authorization, to a report. Built on Kali Linux.

**This folder contains a description only. The code that starts assessment tools is not published.**

## Idea

Beginners often do not know what to do first. The application therefore offers **paths**
(for example "Is my website secure?"). Each path first explains:

- what you **need** (for example a web address),
- what **happens**,
- what you **get** afterwards (knowledge or access).

![Start page with the paths](../bilder/kontrollzentrum/01-startseite.png)

## Core principle: authorization before every check

Before the first start against a target, the application asks for **written authorization**:
who granted it, and the user confirms this explicitly. Without these details no tool starts.
The authorization is stored with a date and appears in every report.

The check is part of the user interface, not of the tools. It sits at the single place
through which every start passes.

![Path preview with a target](../bilder/kontrollzentrum/04-weg-mit-ziel.png)

## Architecture

| Part | Responsibility |
|---|---|
| **Views** | Windows, tabs, path previews, help texts. No execution logic. |
| **Execution** | Starts tools in background threads. Output reaches the window through a **queue**, because Tkinter must only be changed from the main thread. |
| **Data** | Targets, authorizations, progress and reports are plain JSON and Markdown files next to the program. No database. A single environment variable moves the whole data folder, which is what the tests use. |
| **Knowledge** | One text entry per tool with fixed fields: what it is, what to enter, an example, what it gives you, cautions. |
| **Translation** | Raw output of some tools is converted into plain sentences. This is a pure text function and easy to test. |

## Progress and levels

Each finished step counts as a point. Levels (apprentice, scout, examiner, expert) show progress.
Progress is saved after every step and survives a restart.

## Reports

Each assessment can be saved as a Markdown report: target, authorization with date, finished steps and results.
If no authorization exists, the report says so explicitly.

![Toolbox](../bilder/kontrollzentrum/05-werkzeugkiste.png)

## Scope, evidence and findings

- **Scope:** At authorization time you list the IP addresses, networks or domains that may be tested. Any target outside the scope is refused before every start. An authorization can have an expiry date.
- **Run engine:** Runs execute in the background with a queue, a time limit and cancellation (the whole process tree is stopped). Runs that were active when the app closed are marked as interrupted on the next start.
- **Evidence log:** Every run records the command, the exit code, the time and a SHA-256 checksum of its raw output.
- **Findings:** The output of four tools is converted into structured findings (title, severity, detail). Repeated findings across runs are merged using a fingerprint.
- **Suggestions with reasons:** Simple rules state the next sensible step and why (for example "a web service is reachable, so check which software runs first"). There are deliberately no suggestions for attacking.
- **Reports:** Markdown, JSON, CSV and HTML, including authorization, scope, findings and recommendations.

![Findings and suggestions](../bilder/kontrollzentrum/08-befunde.png)

## Test summary

- **13 test areas**, including the run engine on real processes (time limit, cancellation, queue, resume), scope and authorization, the evidence log, parsers, reports in four formats and the user interface. All pass.
- **Lab test:** A local test page that identifies itself as WordPress. Detection and suggestions are correct. Two bugs were found and fixed (color codes in tool output; a web service on an unusual port).
- **Test against a server of my own on the internet:** The firewall only lets SSH through. The scan finds exactly that port and suggests no web step. A password test against SSH was deliberately left out, because the server locks out after failed attempts.
- **Still open:** playbooks (fixed sequences with branches), a view to compare two states, and a measurement against a real practice machine.

## Simple operation (second revision)

- **Start page:** "What do you want to check?" with five categories (website, network, WLAN, files & passwords, reports).
  Below are three recommended checks with an explanation and a rough duration. Technical areas sit behind "Advanced".
- **Preview before every check:** target, permitted scope, steps (with a note when a tool is missing), duration and possible effects.
  Start stays locked until the authorization is confirmed. The scope is checked again before **every** step.
- **Run:** progress ("step 2 of 3"), a clock and a stop button. A missing tool is skipped and the check continues.
- **Plain-language results:** what it is, why it matters, what to do. Raw data and commands stay in the terminal on the right.

![Start page during a check](../bilder/kontrollzentrum/09-startseite-einfach-laeuft.png)
![Plain-language result](../bilder/kontrollzentrum/10-ergebnis-klartext.png)

**Real run (honest):** The quick check ran against my own practice machine; all three steps completed.
The findings were three software notes (Apache, HTTP server, WordPress) and no high-urgency vulnerability.
The known-vulnerability scanner found nothing on this machine. That is a measurement result, not a bug.

## Demo sequence (one example run with sample data)

| Step | Image |
|---|---|
| 1. Start page | ![](../bilder/demo/1-startseite.png) |
| 2. Path with target and authorization | ![](../bilder/demo/2-weg-geraet.png) |
| 3. Result of the step | ![](../bilder/demo/3-ergebnis.png) |
| 4. Result in plain language | ![](../bilder/demo/4-was-heisst-das.png) |

## Testing

- **UI tests** start the window on a virtual display (Xvfb), click through paths, check the authorization gate and progress.
- **Isolated data:** every test writes into its own folder. Real data is never changed. A test run once changed real data by mistake; this is why isolation became a rule.
- **Logic tests:** the recommendation logic and the translation of output are pure functions with their own checks.
- **Bugs found by the tests:** UI calls from background threads (crashes), duplicated grid cells in dialogs, and the data incident above. All fixed.

## Maintenance

The window code was split into separate modules per view (start and paths, targets, steps, toolbox, WLAN, help, assistant).
Unreachable code (an old category view) was removed. Every module is checked with pyflakes.

## What is deliberately not included

- No ready-made attack commands against foreign targets.
- No tool that starts without authorization.
- No storage of access credentials.

## What this shows

Security starts with organization: whoever tests needs permission, must understand what they do, and should document it.
The application makes these steps mandatory before anything starts.
