# Saving Streak — exercises

Start with [project_starter](project_starter/readme.md): deposits earn points immediately, and catalogue rewards are redeemed instantly and finally. Points expiry, deposit tracking, demo login, and funded transfers are already implemented. The loyalty bonus is not implemented. Follow the [business rules](project_starter/saving-streak-spec.md).

Take the **loyalty-rate bonus** through Module 2. Carry its implementation, checks and review findings into Module 3.

## Module 2 — Delivery loop

### 2.1 Shared context

**Goal:** Give a fresh agent the context it needs.

1. Ask the agent to explain the deposit-to-redemption flow, citing relevant code and tests.
2. Add missing repository guidance and domain definitions. Separate project rules from task-specific instructions.
3. Start a fresh session. Ask where the loyalty bonus would fit and check its answer.

**Done when:** You can distinguish the system prompt, repository instructions and task context, and show which information helped the agent.

### 2.2 Intentionality and ambiguity

Ask the agent to interview you and resolve the key decisions about the loyalty-rate bonus feature.

### 2.3 Decomposition and boundaries

First, a short tangent: you receive two versions of the same project, one vibe coded and one agentically engineered. Inspect their [UML diagrams and architecture comparison](docs/uml/README.md) and explore how you would make the same change in each.

- What do we want to achieve, and what do we want to avoid, when asking an LLM to make a plan?
- Why do we need to guide the agent from planning through building and verification?

Then return to your loyalty feature. Use the context you agreed on to split it into testable, verifiable end-to-end slices.

- How would you instruct the model to make that split?
- What makes each slice sufficiently complete to test and verify end to end?

### 2.4 Context

Your feature is split into slices, and its context is saved outside the session conversation.

- What happens when the agent has too much context?
- What happens when that context is compacted?
- Do you need the full feature context to implement every slice?

### 2.5 Execution and implementation

You are ready to implement the first slice.

- When should you start a new session?
- How should you ask the agent to begin implementation?
- Why start with a failing test before writing the implementation (TDD)?

### 2.6 Validation and review

Summon a fresh verifier agent to review the implementer's work.

- Do you trust the implementer's own verification? Why or why not?
- Beyond deterministic checks, what still needs judgment—for example, architecture, UX and the quality of the tests?

### 2.7 Iteration and termination

Your verifier returns with feedback. Start a new implementer session to work through it, then have the changes reviewed again.

- This looks like a loop. Can it be automated?
- How would the loop know when to continue, stop or ask for human input?

### 2.8 Framework comparison

An exposition of spec-driven development, loop engineering and role-based development, connected to the workflow you just followed.

## Module 3 — Platform guardrails

### Exercise 1 — The assembled feature

All tickets for your feature are implemented and merged into one branch.

- What are the next steps?
- Could the assembled feature need additional tests, even if every ticket passed its own checks?
- Which deterministic checks and non-deterministic reviews are appropriate now? Where do CI and review agents fit?
- Why is it still important for a human to review the implementation?
