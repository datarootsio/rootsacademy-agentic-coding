# Saving Streak — exercises

Start with [project_starter](project_starter/readme.md). Earning and redeeming points, points expiry, deposit tracking, demo login, and funded transfers already work. The **loyalty bonus** is the feature you will build.

Follow the [business rules](project_starter/saving-streak-spec.md). Carry your specification, tickets, implementation, and review findings from one exercise to the next.

## Shared context

**What would a fresh agent need?**

- Which code and tests explain deposits and rewards?
- What belongs in repository guidance, and what belongs in the task?

**Outcome:** An AGENTS.md with project guidance, verified in a fresh agent session.

## Intentionality and ambiguity

**What does “loyalty bonus” leave open?**

- Which questions would you want the agent to ask?
- Which examples would settle your answers?

**Outcome:** A saved loyalty-bonus specification with agreed rules and acceptance examples.

## Decomposition and boundaries

**What is the first slice we can prove?**

Compare the [agentic_engineered](docs/uml/agentic_engineered-components.svg) and [vibe_coded](docs/uml/vibe_coded-components.svg) implementations. The [architecture comparison](docs/uml/README.md) also links to their domain diagrams.

- What do the agentic_engineered and vibe_coded diagrams reveal?
- How could you verify one slice of the bonus from end to end?

**Outcome:** Ordered tickets, each with an end-to-end outcome and acceptance checks.

## The context window

**What must survive a fresh session?**

- Which decisions could compaction lose?
- How much of the bonus specification does this slice need?

**Outcome:** A handoff for the first ticket that a fresh session can use without the chat history.

## Execution and implementation

**How would you start the first slice?**

- Would you continue this session or start a fresh one?
- What should the first failing test prove?

**Outcome:** One working slice, with a test that failed before implementation and passes after.

## Validation and review

**What would convince a fresh reviewer?**

- Which claims can tests establish?
- What still needs judgment about the design, UI or tests?

**Outcome:** A fresh agent’s review report, with findings supported by code, tests and the running app.

## Iteration and termination

**When should the loop stop?**

- How will the next agent use the review findings?
- What should trigger another pass or human input?

**Outcome:** Addressed review findings and a follow-up review, with clear stop or escalation criteria.

## Framework comparison

**What does each framework help you check?**

Consider spec-driven development, loop engineering, and role-based workflows in light of the feature you just built.

- Where did specifications, loops and separate roles help?
- Which gaps would remain if you relied on only one?

**Outcome:** A comparison of the three approaches and a reasoned choice for your next feature.

## Platform guardrails

**All tickets pass. Is the feature ready?**

All tickets for the loyalty bonus are implemented and merged into one feature branch.

- Which complete customer journey still needs checking?
- What evidence would a human need before accepting it?

**Outcome:** Evidence from complete user journeys and a recorded human decision to accept the feature or request changes.
