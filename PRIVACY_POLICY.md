# Privacy Policy

Last updated: 2026-09-14

This Privacy Policy explains what data the Discord Playtime Tracker (the "Service") processes and how that data is used.

## 1. Scope
This policy covers the Discord bot, backend API, and dashboard included in this repository.

## 2. Data collected
The Service is designed to collect only data needed for playtime tracking and administration.

Data that may be stored:
- Discord guild ID and guild name.
- Discord user ID, username, display name, and avatar URL.
- Game/activity metadata observed from Discord presence (for example game name and application ID when available).
- Activity session timestamps (start/end) and related metadata.
- Manual playtime entries (historical/imported/correction).
- Manual playtime adjustments and reasons.
- Administrative audit log entries.
- Authentication metadata for dashboard users (username, role, password hash).

## 3. Data not collected
The Service does not collect message content, direct messages, voice recordings, or unrelated Discord private content.

## 4. Purpose of processing
Data is processed to:
- Track and display observed gaming activity.
- Calculate playtime analytics.
- Support manual corrections/imports.
- Provide authentication, authorization, and auditability.

## 5. Legal basis and controller
For self-hosted deployments, the operator of the instance is the data controller and is responsible for selecting an appropriate legal basis under applicable law.

## 6. Data sharing
By default, data is stored in your own deployment and is not sent to a central service by this project. Third-party API calls may occur if you enable integrations (for example Steam profile imports).

## 7. Retention
- Activity session retention may be configured by `SESSION_RETENTION_DAYS`.
- Manual historical/imported records and adjustments are intended to remain until changed or removed by an administrator.
- Audit entries are retained for accountability unless the operator deletes them.

## 8. Security
Security controls include password hashing, role-based authorization, and deployment-level controls. No security system is perfect; operators must secure their infrastructure and secrets.

## 9. Your rights
Depending on local law, users may have rights to access, correct, or delete personal data. For self-hosted deployments, requests should be made to that deployment's administrator.

## 10. International transfers
Data location depends on where the self-hosted instance is deployed. Operators are responsible for compliance with transfer and localization requirements.

## 11. Changes to this policy
This policy may be updated over time. The "Last updated" date indicates the latest revision.

## 12. Contact
For policy questions about a self-hosted instance, contact that instance's administrator. For project-level questions, contact the repository maintainer.
