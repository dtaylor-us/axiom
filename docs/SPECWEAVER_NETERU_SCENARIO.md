# SpecWeaver Test Scenario — Neteru Path

This guide defines a focused SpecWeaver scenario for testing requirements
extraction, classification, gap analysis, conflict detection, readiness scoring,
and Archon handoff.

The application domain is a small Kemetic practice companion inspired by the
teachings of Ra Un Nefer Amen and the Ausar Auset Society. The scenario is
intentionally straightforward to build, but it contains enough architecture
pressure for SpecWeaver to discover privacy, content governance, offline sync,
authorization, auditability, and cultural integrity requirements.

## Objective

Use SpecWeaver to turn messy stakeholder input into an architecture-ready
requirements package for a new app named **Neteru Path**.

The app helps students maintain daily practice around the Neteru through study
notes, hekau reminders, guided meditation, journaling, teacher-assigned practice
cycles, and chapter-specific class materials.

SpecWeaver should identify requirements and risks without treating the app as an
oracle, priesthood replacement, or doctrine generator.

## Recommended Workflow

1. Create a new SpecWeaver session named `Neteru Path`.
2. Ingest each source below as a separate document.
3. Use the suggested `documentType` and `sourceLabel` values so source tracing is
   easy to verify.
4. Generate the package.
5. Review requirements, gaps, conflicts, and readiness score.
6. Use `Send to Archon` only after reviewing the generated brief.

SpecWeaver currently supports these document types:

- `PLAIN_TEXT`
- `MARKDOWN`
- `PDF`
- `DOCX`
- `EMAIL`

Raw text submissions are capped at roughly 500,000 characters. File uploads use
the configured multipart file-size limit, which defaults to 20 MB.

## Source 1 — Founder Notes

Use `documentType=MARKDOWN` and `sourceLabel=Founder notes`.

```markdown
# Neteru Path Founder Notes

We want a simple mobile-first app for people studying Kemetic spirituality and
the teachings of Ra Un Nefer Amen. The app should help users stay consistent with
daily meditation, hekau practice, journaling, and study assignments.

The center of the app should be the Neteru. Users should be able to work with one
Neteru focus at a time, such as Ausar, Auset, Tehuti, Maat, Heru, Het-Heru,
Sebek, Geb, or Seker. Each Neteru profile should include approved teaching
notes, meditation instructions, reflection prompts, and suggested daily actions.

The app must treat the Neteru as spiritual faculties and principles, not as
entertainment, fortune telling, or automated divination. It should not pretend to
be a priest, oracle, or spiritual authority.

Some content should be public. Some content should require enrollment in a
course. Some content should only be visible to a specific chapter or class.
Teachers should be able to create 11-day, 21-day, or 30-day Neteru practice
cycles and assign them to a class.

Users should be able to journal after each practice. Journals may include dreams,
emotional patterns, personal struggles, family matters, goals, health practices,
and spiritual experiences. These journals must be private. Teachers and admins
should not be able to read private journals.

The first version should stay simple and affordable. We do not need a full social
network. Later we may add a Neteru calendar, class announcements, live event
reminders, and audio courses.
```

## Source 2 — Teacher Email

Use `documentType=EMAIL` and `sourceLabel=Teacher email`.

```text
Subject: Requirements for teacher-led practice plans

For the first release, teachers need a way to create a practice plan for a class.
The plan should have a title, Neteru focus, start date, end date, daily practice
instructions, optional audio, and optional reflection prompts.

Teachers need to see completion statistics for the class: who started, who
completed each day, and who is falling behind. They do not need to see journal
content. Maybe they can see whether a journal entry exists, but not the text.

Only approved teachers should publish official Neteru lesson content. Chapter
admins should approve teacher accounts. Platform admins should be able to remove
content if it is inaccurate or uploaded without permission.

We also need to know who changed official content and when. If a lesson is
updated, we should preserve the previous version because people may ask what
changed.

Audio files may include hekau, guided meditations, and short lectures. Some audio
belongs only to a paid course or a chapter. Do not let users download or share
paid audio outside the app.
```

## Source 3 — Student Interview Notes

Use `documentType=PLAIN_TEXT` and `sourceLabel=Student interview notes`.

```text
Several students said they practice early in the morning or late at night. Some
travel often and do not always have a good connection. They want downloaded
practice plans and audio to work offline.

Students want reminders, but they do not want a notification that exposes private
spiritual content on a lock screen. A simple reminder like "practice time" is
fine.

Many students share phones or tablets with family. The app should support a lock
or require re-authentication before opening journals.

Students want streaks and completion history, but they do not want the app to
turn the practice into a game. Progress should feel respectful and simple.

If a student writes journal entries offline for several days, the entries should
sync later without duplicates or overwritten text.
```

## Source 4 — Product Constraint Memo

Use `documentType=MARKDOWN` and `sourceLabel=Product constraint memo`.

```markdown
# Product Constraints

- Initial audience: about 500 users, 5 to 10 teachers, and 3 chapters.
- Growth target: several thousand users internationally.
- Budget: keep hosting inexpensive for version 1.
- First release: account creation, Neteru profiles, practice plans, reminders,
  private journals, offline access to assigned plans, and teacher completion
  stats.
- Later release: class announcements, live event reminders, paid courses, audio
  subscriptions, chapter portals, and Neteru calendar.
- Users may authenticate with email and password in v1. Social sign-in can wait.
- The app should not generate official doctrine or give oracle readings.
- AI may be considered later for summarizing a user's own journal patterns, but
  this must be optional and must not train on user journals.
- Legal language, copyright ownership, retention policy, and delete/export
  requirements are not decided yet.
```

## What SpecWeaver Should Extract

The package should contain a mix of functional requirements, non-functional
requirements, constraints, business rules, data requirements, and assumptions.

Good extraction examples include:

- Users can select or receive a current Neteru focus.
- Neteru profiles contain approved teaching notes, meditation instructions,
  reflection prompts, and daily actions.
- Teachers can create fixed-length practice cycles for classes.
- Teacher analytics must exclude private journal text.
- Private journals must be protected from teacher and admin access.
- Official content changes must be versioned and auditable.
- Public, enrolled, chapter-specific, and class-specific content require access
  control.
- Previously assigned plans and audio should work offline.
- Offline journal entries must sync without duplication or overwrite.
- Notifications must avoid exposing sensitive lock-screen content.
- The app must not provide oracle readings or present itself as spiritual
  authority.
- Hosting should remain inexpensive for the first release.

## Expected Gaps

SpecWeaver should not produce a perfect package from the first pass. Strong gap
analysis should ask about areas such as:

- Data retention for journals, progress history, and audit records.
- Account recovery and shared-device session timeout expectations.
- Encryption expectations for journals at rest and on device.
- Whether admins can recover, export, or delete private journal data.
- Copyright and licensing policy for audio, hekau, lectures, and lesson content.
- Payment or entitlement source of truth for future paid courses.
- Offline cache limits and content revocation behavior.
- Availability targets and recovery expectations.
- Whether teacher analytics are individual-level, aggregate-only, or both.
- Moderation workflow for inaccurate or unauthorized official content.
- International privacy/compliance expectations if the audience grows.

## Expected Conflicts Or Tensions

SpecWeaver should preserve unresolved tensions instead of solving them silently.

Likely conflicts include:

- Teachers want individual completion statistics, while users expect spiritual
  practice privacy.
- Users want offline downloaded audio, while content owners want to prevent
  unauthorized sharing.
- The product wants AI journal summaries later, while journals must remain private
  and must not train models.
- Admins need to remove inaccurate content, while students may need a record of
  what lesson version they previously received.
- The app wants progress tracking, but stakeholders do not want gamified
  spiritual practice.

## Readiness Expectations

A strong first package should probably have a moderate readiness score rather
than a high one. The sources give meaningful scope and constraints, but several
architecture-driving decisions are intentionally missing.

Treat a high readiness score as suspicious if the package does not mention gaps
around privacy, licensing, data retention, offline sync, and content governance.

## Archon Handoff Expectations

The generated brief sent to Archon is capped at 4,000 characters. It should
preserve the system description, summary metrics, top requirements, gaps,
conflicts, and source document labels.

Before sending to Archon, verify that the brief includes these drivers:

- Private journals are not readable by teachers or admins.
- Neteru content requires official source control and versioning.
- Content access differs by public, enrolled, chapter, class, and teacher roles.
- Offline plans, audio, and journal drafts are required.
- The app must not generate doctrine, oracle readings, or spiritual authority
  claims.
- Audit history is required for official content and entitlement changes.

If those drivers are missing from the brief because of truncation, regenerate the
package with fewer or more focused source documents, or manually add the missing
constraints before the Archon chat submission.

## Acceptance Checklist

Use this checklist to judge whether SpecWeaver handled the scenario well.

- Extracts at least one requirement tied to Neteru profiles and practice cycles.
- Classifies privacy, offline use, access control, auditability, and content
  governance as architecture-relevant concerns.
- Keeps private journals separate from teacher-visible progress data.
- Flags licensing, retention, deletion/export, encryption, and session timeout as
  gaps.
- Detects at least one conflict involving offline access, teacher analytics,
  content control, AI summaries, or privacy.
- Preserves source traceability with document IDs or source labels.
- Produces a concise Archon-ready brief that includes the most important
  architecture drivers.
- Does not invent doctrine, prescribe religious interpretation, or resolve
  spiritual authority questions on behalf of stakeholders.

## Clarifying Answers For A Second Pass

If you want to test whether a second SpecWeaver run improves readiness, add this
as another document after the first package review.

Use `documentType=PLAIN_TEXT` and `sourceLabel=Stakeholder clarification answers`.

```text
Private journal entries should be encrypted at rest and should not be readable by
teachers, chapter admins, or platform admins. Users may export or delete their
own journal entries. Deleted journal entries should be removed from active
application views within 30 days unless legal retention is required.

Practice completion status may be visible to assigned teachers at the individual
level, but journal text is never visible. Teachers can see whether a journal
entry exists for a day, but not the entry content.

Official Neteru content must have version history, author attribution, reviewer
approval, publication status, and an audit trail. Published lessons can be
retired but should not be physically deleted.

Downloaded audio should be playable offline only inside the app. Revoked or
expired entitlements should remove offline access the next time the device
connects.

The app should support 99.5% monthly availability for v1. Practice reminders may
be delayed up to 30 minutes. Journal sync should retry automatically and avoid
duplicate entries.

User sessions should expire after 30 days on personal devices and after 30
minutes of inactivity when app lock is enabled. Journals should require
re-authentication or local device unlock.
```

After adding this source, the next package should show fewer critical gaps,
stronger privacy requirements, clearer audit and entitlement requirements, and a
more useful Archon handoff.
