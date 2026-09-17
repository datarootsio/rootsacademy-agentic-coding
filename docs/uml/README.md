# Saving Streak architecture comparison

These diagrams are workshop reference snapshots, copied into this presentation. They describe the two comparison implementations, not branches of this repository. Package and stylesheet labels in the simpler implementation have been generalized for presentation.

Two **component / architecture diagrams**, read directly from the committed branch snapshots on 2026-09-17. Uncommitted working-tree changes are excluded. The repository branch named `vibe_coded` is the “vibecoded” branch requested. The earlier domain class diagrams are retained below as supplementary material.

## Component architecture

| Branch | Snapshot | View | Editable source | PNG |
| --- | --- | --- | --- | --- |
| `agentic_engineered` | `0ba5c12` | [SVG](agentic_engineered-components.svg) | [PlantUML](agentic_engineered-components.puml) | [PNG](agentic_engineered-components.png) |
| `vibe_coded` | `552050f` | [SVG](vibe_coded-components.svg) | [PlantUML](vibe_coded-components.puml) | [PNG](vibe_coded-components.png) |

The diagrams cover browser frontend, HTTP API, backend responsibilities, persistence, SQLite, and time/scheduling infrastructure. Components represent responsibilities inside a single backend application. They do not imply separate deployable services.

| Concern | `agentic_engineered` | `vibe_coded` |
| --- | --- | --- |
| Frontend | React + TypeScript; Vite development server proxies `/api` | Vanilla JavaScript and static assets served by Spring Boot |
| API | Customer, savings-account and reward controllers; additional development endpoints | One `ApiController`; services construct `web.dto` responses |
| Backend organization | Feature packages with service boundaries and local repositories | Shared `service`, `repo`, and `domain` packages |
| Coordination | Controllers compose feature calls; feature modules collaborate | Command services use `OverviewService` for lookups and refreshed responses |
| Time-dependent work | Scheduled points expiry, loyalty payout and notification sweeps | Loyalty and notifications evaluated on access; points validity checked at read/spend time |
| Development facilities | Movable persisted clock and on-demand invocation of scheduled methods | Demo seeding/reset; configured system clock |
| Persistence | Spring Data JPA/Hibernate repositories inside feature packages | Nine shared Spring Data JPA repositories |

Arrows between business components were checked against the branch source. API routing and repository access are aggregated; repeated clock injection edges are omitted. The deposits/streaks dependency cycle in `agentic_engineered` is shown: deposits call the streak derivation, which reads deposit history. It is a code dependency cycle, not a claim of infinite runtime recursion.

In `vibe_coded`, **Commands** groups `BankingService`, `GiftService`, `RewardService`, and `ContactService`; **Points** groups `PointsWallet` and `PointsRules`. These are diagram groupings, not additional packages. An outgoing arrow means at least one grouped class uses the target.

Pinned commits: `0ba5c12052f2521d55d1b5c7a29de9c18dae2c3a` and `552050f682400bfc928ab1efe8c0ced1ceee13cd`. All component diagrams were rendered and visually inspected.

## Supplementary domain class diagrams

| Branch | Snapshot | View | Editable source | PNG |
| --- | --- | --- | --- | --- |
| `agentic_engineered` | `0ba5c12` | [SVG](agentic_engineered.svg) | [PlantUML](agentic_engineered.puml) | [PNG](agentic_engineered.png) |
| `vibe_coded` | `552050f` | [SVG](vibe_coded.svg) | [PlantUML](vibe_coded.puml) | [PNG](vibe_coded.png) |

Open an SVG in a browser to zoom without losing clarity.

Both diagrams show business entities, selected fields and operations, key enums, and logical relationship multiplicities. Constructors, accessors, controllers, services, repositories, DTOs, infrastructure, and frontend code are omitted. Package boundaries match the source. The `ClockOffset` development entity is outside this domain view.

Relationship labels name the reference field. In `agentic_engineered`, account-to-customer links are JPA object relationships; other entity links are scalar IDs. In `vibe_coded`, all depicted entity relationships use scalar IDs. Multiplicities describe normal application data, not database-enforced foreign keys or historical migration states. Repeated customer links and the polymorphic `PointsCredit.sourceReferenceId` are documented without drawing every edge.

The main differences visible in the diagrams:

| Concern | `agentic_engineered` | `vibe_coded` |
| --- | --- | --- |
| Organization | Entities grouped by feature package | Entities together in `domain` |
| Accounts | Separate `CurrentAccount` and `SavingsAccount`, both referencing `Customer` | One `Account` with an `AccountType`; no stored member reference |
| Money movements | `Deposit`, `Withdrawal`, and `WithdrawalAllocation` | `Transfer` with deposit, withdrawal, and rebalance directions |
| Savings balance | Derived from deposits' remaining amounts | Stored as `Account.balanceCents` |
| Streak | Derived from deposit history | State stored on `Member` |
| Loyalty | Remaining deposit principal and `LoyaltyBonusPaid` anniversary records | Movable/splittable `SavingsPosition` with anniversary counters |
| Points | `PointsCredit`, separate accrual/streak reasons, expiry recorded by a sweep | `PointsLot`, explicit expiry timestamp, validity evaluated on access |
| Rewards | Fixed `Reward` enum | Persisted `Reward` entity |

Source roots: `backend/src/main/java/io/dataroots/savingstreak/` at `agentic_engineered`, and the Java application source at `vibe_coded`.

Rendered with PlantUML 1.2024.8 using its built-in Smetana layout. To regenerate from the repository root with a PlantUML JAR:

```sh
java -Djava.awt.headless=true -jar /path/to/plantuml.jar -tsvg docs/uml/*.puml
java -Djava.awt.headless=true -jar /path/to/plantuml.jar -tpng docs/uml/*.puml
```

The depicted class names, field names/types, and operation names were checked against the pinned source snapshots. Both diagrams were rendered and visually inspected.
