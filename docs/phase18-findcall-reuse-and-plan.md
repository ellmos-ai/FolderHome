# Phase 18: FindCall Reuse and Blueprint

**English** | [Deutsch](./phase18-findcall-reuse-and-plan.de.md)

**Status:** 2026-08-22  
**Status:** Provider inventory, generic contract and Fixture CLI completed

## User Goal

FindCall shall contact suitable providers sequentially until a request is successful within previously defined limits. Core cases are a medical appointment within a time window, a workshop appointment with a cost estimate, and obtaining comparable offers. Real phone calls, reservations, and financial commitments remain outside the local competitive assessment.

## Verified Inventory

### HungryCall, Revision `2c7db533f073d07eae6d758ceab91b9423ae1dc7`

- Checkout and manifest are clean, version `0.1.0`, MIT; 301 provider tests ran locally green.
- Reusable is the generalized cascade principle: filter and sort candidates, contact them serially, evaluate structured results against mandatory, price, and concession limits, and stop after the first success.
- E.164 validation, masked outputs, Idempotency-Key, differentiated call status, and a network‑less fixture client are already in place.
- The concrete runtime is intentionally typed to restaurant, order, pickup, and table reservation. Medical, workshop, or offer models must not be forced into restaurant data.

### Ringedingeding, Revision `55f426598d716991b0fae8c5e1c092aceb8c4da8`

- Checkout and manifest are clean, version `0.1.0`, MIT; the full provider suite ran locally green.
- Reusable are schema‑driven queries to multiple known persons, stable Idempotency‑Keys, received final status, masked numbers, and the local `FixtureTransport`.
- The product resolves group availability, selection questions, and open feedback. This is not a provider search run and does not have an early stop after the first suitable offer.

## Responsibility Boundaries

```text
HungryCall
  behält seine Gastronomie-Runtime und liefert das geprüfte Kaskadenmuster

Ringedingeding
  behält Mehrpersonen-Polls und Terminabstimmungen mit bekannten Kontakten

FindCall
  modelliert generische Anbieter, Anfragegrenzen und den seriellen Suchlauf

FolderHome
  prüft Pins, wählt den Anwendungsfall und hält Live-Gates geschlossen
```


FolderHome loads both providers only from the exactly pinned, clean checkout. A plugin probe may test only local classes and dry‑run properties. The new FindCall core resides encapsulated under `folderhome.capabilities.findcall` and does not import restaurant or poll data types into its public contracts.

## FindCall Contract V1

1. A request specifies an organizational profile, domain, request type, service description, location, at least one time window, optional price ceiling, and expressly permitted commitment.
2. V1 supports `appointment` and `quote`. Medical information is limited to specialty and administrative appointment conditions; symptoms, diagnoses, and emergencies are rejected.
3. Candidates have stable local IDs, name, maskable E.164 number, optional distance and priority. Plain numbers never appear in plan or report.
4. Pre‑filtering removes unsuitable services, excessive distance, or missing contact capability. The remaining candidates are deterministically ordered by priority, distance, and ID.
5. The dry‑run operates strictly serially. It preserves `NO_ANSWER`, `BUSY`, `DECLINED`, `FAILED` and `COMPLETED`, evaluates structured results, and stops after the first result within all limits.
6. `inquiry_only` may neither book nor issue an order. A later binding action requires its own concrete live approval and will not be implemented in Phase 18.
7. Fixture results are expressly `simulated=true`, perform no network access, and are not presented as actual availability or price commitment.

## Use Cases

### USECASE 018-1: Search for Medical Appointment

- **Input:** Specialty dermatology, location, two time windows, three synthetic practices, `inquiry_only`.
- **Expectation:** The first unreachable candidate remains visible; the second suitable fixture appointment ends the cascade. No booking occurs.

### USECASE 018-2: Evaluate Workshop Offer

- **Input:** Brake inspection for Hyundai i10, time window and maximum cost estimate.
- **Expectation:** An unclear or overly expensive offer is rejected; the first precise offer within the limit is reported as a simulated hit.

### USECASE 018-3: No Suitable Option

- **Input:** Multiple synthetic providers whose results miss status or mandatory limits.
- **Expectation:** All attempts remain with a concrete reason; success and external side effects are `false`.

### USECASE 018-4: Verify Plugin Pins

- **Input:** FolderHome manifests and local provider checkouts.
- **Expectation:** HungryCall and Ringedingeding are accepted only with exact version, revision, clean Git status, and an available dry‑run entry point.

## Acceptance Boundary

Phase 18 is completed with 170 FolderHome tests. Plugin probe, FindCall plan, serial fixture run, and CLI are green on synthetic data. No real phone numbers, accounts, networks, appointments, workshop orders, or costs were triggered.
