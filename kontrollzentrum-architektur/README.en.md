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
