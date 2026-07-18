---
name: deepworkplan
description: Create, execute, and manage structured Deep Work Plans for this repository
version: "2.15.0"
documentation_url: https://deepworkplan.com
---

# DeepWorkPlan Skill

Manage structured, multi-task Deep Work Plans for this repository.

## Available Commands

| Command | Description |
|---------|-------------|
| `/dwp-create` | Create a new Deep Work Plan |
| `/dwp-execute` | Execute an existing plan |
| `/dwp-refine` | Refine a draft plan |
| `/dwp-resume` | Resume an interrupted plan |
| `/dwp-status` | Check plan status |
| `/dwp-verify` | Verify AI-first conformance |

## About

DeepWorkPlan turns this repository into a structured environment where AI coding agents can execute reliably on long-horizon work. Plans are stored in `.dwp/plans/` and drafts in `.dwp/drafts/`.

## Skill Location

This skill is installed at: `.agents/skills/deepworkplan/`

The skill is the single source of truth — do not copy or duplicate its sub-skills.
