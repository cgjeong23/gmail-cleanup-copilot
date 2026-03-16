# Gmail Cleanup Copilot

Human-in-the-loop Gmail cleanup assistant with automated monthly reporting.

Modern inboxes accumulate large volumes of automated and promotional emails. While email clients provide filters and unsubscribe links, they rarely offer a structured way to understand which senders contribute most to inbox clutter.

As a result, inbox cleanup often becomes a repetitive and manual task.

Gmail Cleanup Copilot analyzes Gmail activity at the sender level, identifies low-value senders, and produces ranked cleanup recommendations with explanations.

The system combines data analysis, explainable ranking, and workflow automation to turn inbox cleanup from an ad-hoc task into a structured process.
---
## Problem

Large inboxes often contain hundreds of automated notifications, newsletters, and marketing emails.

Existing email tools provide limited support for answering questions such as:

* Which senders contribute most to inbox clutter?
* Which sources send high-frequency low-value emails?
* Which messages can be safely cleaned up?

Without sender-level visibility, users must manually inspect individual emails, making inbox cleanup inefficient and repetitive.
---
## Solution

Gmail Cleanup Copilot introduces a sender-level inbox analysis pipeline that aggregates Gmail activity and ranks cleanup candidates.

The system operates in two complementary modes:

### Interacrtive Cleanup Dashboard

A Streamlit interface that visualizes sender activity and allows users to review cleanup candidates before taking action.

Features include:

* ranked sender recommendations
* explainable cleanup reasons
* sender-level inbox insights
* human approval before cleanup actions

### Automated Monthly Reporting

A scheduled workflow that analyzes inbox activity and generates a monthly cleanup report.

The report sumarizes:

* sender activity
* cleanup candidates
* review candidates
* inbox clutter trends

The report is automatically generated and delivered via email using an orchestrated workflow.
---
