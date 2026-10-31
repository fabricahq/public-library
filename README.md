# Fabrica Public Library

<p>
  <a href="LICENSE.md"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://github.com/fabricahq/trailguide"><img alt="A Trail Guide library" src="https://img.shields.io/badge/Trail%20Guide-library-6f42c1"></a>
  <img alt="14 groups, 130 rules" src="https://img.shields.io/badge/rules-130-brightgreen">
</p>

Fabrica Public Library is a collection of engineering rules and skills that tell coding agents how to write and review production-grade code. Each rule covers one practice, such as reproducing a bug with a test before fixing it, or narrowing unknown values in TypeScript, with examples of what to do, what to avoid, and what a reviewer should check.

The rules live in `.trailguide/rules/` and are organized into groups. Practice groups (`practices/`) apply in any language, and technology groups (`techs/`) cover one language, framework, or tool. You choose the groups that match your stack, and you can leave out any rule you disagree with.

## What rules are included?

| Group | Rules | Description |
| --- | --: | --- |
| [Testing](.trailguide/rules/practices/testing/) | 8 | Where to spend testing effort, and how to write tests that stay reliable |
| [Code design](.trailguide/rules/practices/code-design/) | 5 | Designing interfaces, functions, modules, folders, and recorded state so code stays readable and correct |
| [Concurrency](.trailguide/rules/practices/concurrency/) | 2 | Keeping shared resources usable and honoring cancellation throughout blocking operations |
| [Performance](.trailguide/rules/practices/performance/) | 1 | Making code faster where measurement shows it matters |
| [READMEs](.trailguide/rules/practices/readmes/) | 5 | Writing READMEs that say what a product does for the reader, get them to a first result, and fit the product's tier |
| [TypeScript](.trailguide/rules/techs/typescript/) | 19 | Writing type-safe, maintainable TypeScript |
| [JavaScript](.trailguide/rules/techs/javascript/) | 8 | Async work, browser APIs, and build-friendly code in JavaScript and TypeScript |
| [React](.trailguide/rules/techs/react/) | 39 | Building correct, accessible, and fast React interfaces, on the client and server |
| [TanStack Query](.trailguide/rules/techs/tanstack-query/) | 15 | Fetching, caching, and updating server data with TanStack Query |
| [TanStack Router](.trailguide/rules/techs/tanstack-router/) | 10 | Typed routing, data loading, and navigation with TanStack Router |
| [Zustand](.trailguide/rules/techs/zustand/) | 10 | Managing shared client state with Zustand |
| [Playwright](.trailguide/rules/techs/playwright/) | 2 | Writing stable browser tests with Playwright |
| [Go](.trailguide/rules/techs/go/) | 5 | Writing clear, maintainable Go |
| [Goose](.trailguide/rules/techs/goose/) | 1 | Organizing SQL migrations managed by goose |

### Browse all 130 rules

<details>
<summary><strong>Testing</strong> · 8 rules</summary>

- [Choose tests by risk and cost](.trailguide/rules/practices/testing/choose-tests-by-risk.md)
- [Cover empty inputs and boundaries](.trailguide/rules/practices/testing/cover-boundary-cases.md)
- [Keep tests independent](.trailguide/rules/practices/testing/keep-tests-independent.md)
- [Name tests for the behavior and the condition](.trailguide/rules/practices/testing/name-tests-for-behavior-and-condition.md)
- [Run focused tests while iterating, and the full suite before finishing](.trailguide/rules/practices/testing/run-focused-tests-while-iterating.md)
- [Test at the lowest layer that proves the behavior](.trailguide/rules/practices/testing/test-at-the-lowest-layer.md)
- [Reproduce bugs with regression tests](.trailguide/rules/practices/testing/test-bug-fixes-before-fixing.md)
- [Test observable behavior](.trailguide/rules/practices/testing/test-observable-behavior.md)

</details>

<details>
<summary><strong>Code design</strong> · 5 rules</summary>

- [Express operations as meaningful steps](.trailguide/rules/practices/code-design/express-operations-as-meaningful-steps.md)
- [Hide implementation decisions behind meaningful interfaces](.trailguide/rules/practices/code-design/hide-implementation-decisions.md)
- [Organize code by feature](.trailguide/rules/practices/code-design/organize-code-by-feature.md)
- [Record facts when they happen](.trailguide/rules/practices/code-design/record-facts-when-they-happen.md)
- [Separate pure computation from effects](.trailguide/rules/practices/code-design/separate-pure-computation-from-effects.md)

</details>

<details>
<summary><strong>Concurrency</strong> · 2 rules</summary>

- [Honor cancellation and deadlines across every blocking stage](.trailguide/rules/practices/concurrency/honor-cancellation-across-blocking-stages.md)
- [Keep shared resources alive until their users finish](.trailguide/rules/practices/concurrency/keep-shared-resources-alive-until-users-finish.md)

</details>

<details>
<summary><strong>Performance</strong> · 1 rule</summary>

- [Optimize measured hot paths by removing repeated work](.trailguide/rules/practices/performance/optimize-measured-hot-paths.md)

</details>

<details>
<summary><strong>READMEs</strong> · 5 rules</summary>

- [Give a quick start that runs as written](.trailguide/rules/practices/readmes/give-a-quick-start-that-runs-as-written.md)
- [Keep the README an entry point, and link to the full documentation](.trailguide/rules/practices/readmes/keep-the-readme-an-entry-point.md)
- [Match the README's presentation to the product's tier](.trailguide/rules/practices/readmes/match-presentation-to-product-tier.md)
- [Open with what the product does for the reader](.trailguide/rules/practices/readmes/open-with-what-the-product-does.md)
- [State what the product does not do](.trailguide/rules/practices/readmes/state-what-the-product-does-not-do.md)

</details>

<details>
<summary><strong>TypeScript</strong> · 19 rules</summary>

- [Annotate types at module boundaries and where they narrow](.trailguide/rules/techs/typescript/annotate-types-at-boundaries.md)
- [Avoid silencing the type checker](.trailguide/rules/techs/typescript/avoid-silencing-the-type-checker.md)
- [Comment the role, the result, and the hidden constraint](.trailguide/rules/techs/typescript/comment-role-result-and-constraints.md)
- [Declare constants with as const, and satisfies when a type exists](.trailguide/rules/techs/typescript/declare-constants-with-as-const.md)
- [Distinguish null from undefined](.trailguide/rules/techs/typescript/distinguish-null-from-undefined.md)
- [Generate service types from their contracts](.trailguide/rules/techs/typescript/generate-service-types-from-contracts.md)
- [Model distinct states as discriminated unions](.trailguide/rules/techs/typescript/model-variants-as-discriminated-unions.md)
- [Narrow unknown values before use](.trailguide/rules/techs/typescript/narrow-unknown-values.md)
- [Prefer literal unions over enums](.trailguide/rules/techs/typescript/prefer-literal-unions-over-enums.md)
- [Prefer type aliases over interfaces](.trailguide/rules/techs/typescript/prefer-type-aliases.md)
- [Preserve caller-owned data](.trailguide/rules/techs/typescript/preserve-caller-owned-data.md)
- [Make properties and parameters required, and name them](.trailguide/rules/techs/typescript/require-properties-and-name-parameters.md)
- [Import types with import type](.trailguide/rules/techs/typescript/separate-type-imports.md)
- [Use Boolean() for explicit boolean coercion](.trailguide/rules/techs/typescript/use-boolean-for-explicit-boolean-coercion.md)
- [Follow consistent naming conventions](.trailguide/rules/techs/typescript/use-consistent-naming.md)
- [Use one array type syntax](.trailguide/rules/techs/typescript/use-generic-array-types.md)
- [Use named exports](.trailguide/rules/techs/typescript/use-named-exports.md)
- [Use predictable file names](.trailguide/rules/techs/typescript/use-predictable-file-names.md)
- [Use template literal types for patterned strings](.trailguide/rules/techs/typescript/use-template-literal-types-for-patterned-strings.md)

</details>

<details>
<summary><strong>JavaScript</strong> · 8 rules</summary>

- [Avoid layout thrashing](.trailguide/rules/techs/javascript/avoid-layout-thrashing.md)
- [Await only on paths that need the result](.trailguide/rules/techs/javascript/await-only-on-paths-that-need-the-result.md)
- [Defer non-critical browser work to idle time](.trailguide/rules/techs/javascript/defer-non-critical-work-to-idle-time.md)
- [Keep dynamic import and file paths statically analyzable](.trailguide/rules/techs/javascript/keep-import-and-file-paths-analyzable.md)
- [Load measurement scripts the way their vendors document](.trailguide/rules/techs/javascript/load-measurement-scripts-as-documented.md)
- [Start independent asynchronous work concurrently](.trailguide/rules/techs/javascript/start-independent-async-work-concurrently.md)
- [Mark scroll-related listeners passive when they never cancel scrolling](.trailguide/rules/techs/javascript/use-passive-scroll-and-touch-listeners.md)
- [Version and minimize data in browser storage](.trailguide/rules/techs/javascript/version-and-minimize-browser-storage.md)

</details>

<details>
<summary><strong>React</strong> · 39 rules</summary>

- [Give every interactive element a role and an accessible name](.trailguide/rules/techs/react/accessibility-roles-and-names.md)
- [Run app-wide initialization once per app load](.trailguide/rules/techs/react/advanced-init-once.md)
- [Build complex components from composable parts](.trailguide/rules/techs/react/architecture-compound-components.md)
- [Create explicit component variants instead of boolean mode props](.trailguide/rules/techs/react/architecture-explicit-variants.md)
- [Stream slow data behind Suspense boundaries](.trailguide/rules/techs/react/async-suspense-boundaries.md)
- [Avoid loading large barrel files](.trailguide/rules/techs/react/bundle-barrel-imports.md)
- [Keep non-critical scripts off the critical path](.trailguide/rules/techs/react/bundle-defer-non-critical-scripts.md)
- [Load heavy optional code on demand](.trailguide/rules/techs/react/bundle-load-heavy-code-on-demand.md)
- [Share client data requests through a caching data layer](.trailguide/rules/techs/react/client-share-data-requests.md)
- [Read the latest callbacks in Effects without resubscribing](.trailguide/rules/techs/react/effects-read-latest-values-without-resubscribing.md)
- [Name generic components by capability, not by first caller](.trailguide/rules/techs/react/generic-components-by-capability.md)
- [Name Effect and non-trivial Hook callbacks](.trailguide/rules/techs/react/hooks-name-callbacks.md)
- [Avoid copying props to state](.trailguide/rules/techs/react/official-avoid-copying-props-to-state.md)
- [Avoid unnecessary Effects](.trailguide/rules/techs/react/official-avoid-unnecessary-effects.md)
- [Follow the Rules of Hooks](.trailguide/rules/techs/react/official-follow-rules-of-hooks.md)
- [Keep components and Hooks pure](.trailguide/rules/techs/react/official-keep-components-and-hooks-pure.md)
- [Accept ref as a prop in React 19](.trailguide/rules/techs/react/react19-no-forwardref.md)
- [Use Activity to hide UI that should keep its state](.trailguide/rules/techs/react/rendering-activity.md)
- [Use a boolean condition for conditional rendering](.trailguide/rules/techs/react/rendering-conditional-render.md)
- [Skip off-screen rendering work in long lists](.trailguide/rules/techs/react/rendering-content-visibility.md)
- [Render client-only preferences without a flash or hydration error](.trailguide/rules/techs/react/rendering-hydration-no-flicker.md)
- [Suppress only expected hydration mismatches](.trailguide/rules/techs/react/rendering-hydration-suppress-warning.md)
- [Hint critical resources with React DOM resource APIs](.trailguide/rules/techs/react/rendering-resource-hints.md)
- [Subscribe to and depend on only the values you use](.trailguide/rules/techs/react/rerender-depend-on-narrow-values.md)
- [Use functional updates when new state depends on old state](.trailguide/rules/techs/react/rerender-functional-setstate.md)
- [Initialize expensive state lazily](.trailguide/rules/techs/react/rerender-lazy-state-init.md)
- [Keep input responsive by marking non-urgent updates](.trailguide/rules/techs/react/rerender-mark-non-urgent-updates.md)
- [Memoize deliberately](.trailguide/rules/techs/react/rerender-memoize-deliberately.md)
- [Do not define components inside components](.trailguide/rules/techs/react/rerender-no-inline-components.md)
- [Keep values that do not affect rendering in refs](.trailguide/rules/techs/react/rerender-use-ref-transient-values.md)
- [Run post-response work after the response](.trailguide/rules/techs/react/server-after-nonblocking.md)
- [Authenticate and authorize inside every Server Action](.trailguide/rules/techs/react/server-auth-actions.md)
- [Deduplicate per-request server work with cache](.trailguide/rules/techs/react/server-cache-react.md)
- [Pass only the data Client Components use](.trailguide/rules/techs/react/server-minimize-serialized-props.md)
- [Keep request data out of shared module state](.trailguide/rules/techs/react/server-no-shared-module-state.md)
- [Compose independent server data fetches as siblings](.trailguide/rules/techs/react/server-parallel-fetching.md)
- [Reuse request-independent server data across requests](.trailguide/rules/techs/react/server-reuse-request-independent-data.md)
- [Lift shared component state into a provider behind an interface](.trailguide/rules/techs/react/state-lift-shared-state-into-providers.md)
- [Give repeated and persistent surfaces stable test ids](.trailguide/rules/techs/react/testing-ship-stable-e2e-scope-test-ids.md)

</details>

<details>
<summary><strong>TanStack Query</strong> · 15 rules</summary>

- [Use initialData only for complete data](.trailguide/rules/techs/tanstack-query/cache-placeholder-vs-initial.md)
- [Set staleTime from how fast data changes](.trailguide/rules/techs/tanstack-query/cache-stale-time.md)
- [Reset query errors when an error boundary retries](.trailguide/rules/techs/tanstack-query/err-error-boundaries.md)
- [Derive infinite query page params from the server's response](.trailguide/rules/techs/tanstack-query/inf-page-params.md)
- [Invalidate or update every query a mutation changes](.trailguide/rules/techs/tanstack-query/mut-invalidate-queries.md)
- [Read mutation state from other components with useMutationState](.trailguide/rules/techs/tanstack-query/mut-mutation-state.md)
- [Make optimistic updates reversible, and decide them once](.trailguide/rules/techs/tanstack-query/mut-optimistic-updates.md)
- [Make offline behavior explicit](.trailguide/rules/techs/tanstack-query/offline-behavior.md)
- [Fetch a dynamic set of queries with useQueries](.trailguide/rules/techs/tanstack-query/parallel-use-queries.md)
- [Derive component views of query data with a stable select](.trailguide/rules/techs/tanstack-query/perf-select-transform.md)
- [Prefetch likely next data on user intent](.trailguide/rules/techs/tanstack-query/pf-intent-prefetch.md)
- [Define hierarchical query keys and options in factories](.trailguide/rules/techs/tanstack-query/qk-factory-pattern.md)
- [Key each query by every input it uses](.trailguide/rules/techs/tanstack-query/qk-include-dependencies.md)
- [Pass the query's AbortSignal to the request](.trailguide/rules/techs/tanstack-query/query-cancellation.md)
- [Prefetch on the server and hydrate the query cache](.trailguide/rules/techs/tanstack-query/ssr-dehydration.md)

</details>

<details>
<summary><strong>TanStack Router</strong> · 10 rules</summary>

- [Provide shared dependencies through typed router context](.trailguide/rules/techs/tanstack-router/ctx-router-context.md)
- [Throw notFound for missing resources and render it with notFoundComponent](.trailguide/rules/techs/tanstack-router/err-not-found.md)
- [With TanStack Query, load route data into the Query cache](.trailguide/rules/techs/tanstack-router/load-ensure-query-data.md)
- [Load route data in loaders, in parallel](.trailguide/rules/techs/tanstack-router/load-use-loaders.md)
- [Use Link for navigation users can open, and redirect in the router](.trailguide/rules/techs/tanstack-router/nav-link-component.md)
- [Mask modal routes with the resource's canonical URL](.trailguide/rules/techs/tanstack-router/nav-route-masks.md)
- [Set app-wide navigation behavior in router defaults](.trailguide/rules/techs/tanstack-router/router-default-options.md)
- [Validate search params with defaults at the route](.trailguide/rules/techs/tanstack-router/search-validation.md)
- [Split route components out of the main bundle](.trailguide/rules/techs/tanstack-router/split-route-code.md)
- [Register the router and read route data through typed route APIs](.trailguide/rules/techs/tanstack-router/ts-route-type-inference.md)

</details>

<details>
<summary><strong>Zustand</strong> · 10 rules</summary>

- [Create stores once, outside render](.trailguide/rules/techs/zustand/create-stores-at-module-scope.md)
- [Define typed state and named actions](.trailguide/rules/techs/zustand/define-typed-state-and-named-actions.md)
- [Keep store state serializable](.trailguide/rules/techs/zustand/keep-store-state-serializable.md)
- [Keep each store focused on one domain](.trailguide/rules/techs/zustand/keep-stores-domain-focused.md)
- [Persist only safe, versioned state](.trailguide/rules/techs/zustand/persist-only-safe-versioned-state.md)
- [Rehydrate persisted stores after React hydration](.trailguide/rules/techs/zustand/rehydrate-persisted-stores-after-hydration.md)
- [Subscribe with narrow, stable selectors](.trailguide/rules/techs/zustand/subscribe-with-selectors.md)
- [Reset stores between tests and test actions directly](.trailguide/rules/techs/zustand/test-actions-and-reset-stores.md)
- [Update store state functionally and immutably](.trailguide/rules/techs/zustand/use-functional-and-immutable-updates.md)
- [Use Zustand only for shared client state](.trailguide/rules/techs/zustand/use-zustand-only-for-shared-client-state.md)

</details>

<details>
<summary><strong>Playwright</strong> · 2 rules</summary>

- [Synchronize with auto-waiting actions and web-first assertions](.trailguide/rules/techs/playwright/auto-waiting-actions-and-web-first-assertions.md)
- [Scope locators by test id, then select controls by role and name](.trailguide/rules/techs/playwright/domain-scope-and-user-facing-locators.md)

</details>

<details>
<summary><strong>Go</strong> · 5 rules</summary>

- [Comment struct fields whose meaning the type does not show](.trailguide/rules/techs/go/comment-non-obvious-struct-fields.md)
- [Separate package documentation from file headers](.trailguide/rules/techs/go/comments-package-doc-vs-file-header.md)
- [Add operation and identifier context to errors at boundaries](.trailguide/rules/techs/go/errors-include-useful-diagnostic-data.md)
- [Expose error identity only for contract errors](.trailguide/rules/techs/go/errors-use-contract-errors-deliberately.md)
- [Give text and its parsed form one owner](.trailguide/rules/techs/go/one-owner-for-text-and-parsed-form.md)

</details>

<details>
<summary><strong>Goose</strong> · 1 rule</summary>

- [Keep the SQL migration directory for migration files only](.trailguide/rules/techs/goose/migrations-directory-contains-only-sql.md)

</details>

## What skills are included?

Skills are step-by-step procedures for one kind of task, installed into the folders your agents read. The library recommends these; a project installs them by including `recommended` from this source.

- [build](.trailguide/skills/fabrica/build/SKILL.md): build one planned slice of work while you're away. The agent settles a done condition, decides reversible calls itself, works in small verified units, proves the result on the running app, and hands back a decision log for you to review. It follows the Build stage of [the Fabrica book](https://fabricahq.com/book).
- [create-verification-skill](.trailguide/skills/pstack/create-verification-skill/SKILL.md): generate a project-local skill that launches the real app, drives its user-facing features, records proof, and cleans up. Includes a feature-map example and requires a successful end-to-end run before hand-back.
- [maintain-verification-skill](.trailguide/skills/pstack/maintain-verification-skill/SKILL.md): check an existing verification skill against source and live behavior, then open one PR for proven documentation, harness, or feature-map corrections. Product regressions are reported separately.
- [ratchet-files](.trailguide/skills/dzhng/ratchet-files/SKILL.md): keep every source file small enough for an agent to read in one pass. Find files over a token budget, split them by concept, and set up the pre-commit ratchet that stops them from growing. Adapted from [dzhng/skills](https://github.com/dzhng/skills).

`build` calls nine skills from [pstack](https://github.com/cursor/plugins/tree/main/pstack), Lauren Tan's skill collection, and they install with it. Eight are pstack principles the library curates as dependencies, so they install only with `build`: `principle-attack-the-premise`, `principle-build-the-lever`, `principle-fix-root-causes`, `principle-guard-the-context-window`, `principle-laziness-protocol`, `principle-never-block-on-the-human`, `principle-prove-it-works`, and `principle-sequence-verifiable-units`. The library pins them to a pstack commit it has reviewed, and moves the pin only in a new library release. The ninth, [show-me-your-work](.trailguide/skills/pstack/show-me-your-work/SKILL.md), is the library's adaptation of pstack's decision log, which works in any agent harness and has a Codex agent review Claude's work, or the reverse.

The two verification skills are also adapted from the pinned pstack source. Both are recommended and can be selected independently. Neither calls a fixed skill: creation offers maintenance as a later task, while maintenance discovers the project's authored verification skill and suggests creation only when no target exists. These suggestions are not `trailguide-skills-used` dependencies, so installing either one alone does not install the other. Their bundled references are ordinary files, not additional skills.

## How does it relate to Trail Guide?

[Trail Guide](https://github.com/fabricahq/trailguide) is the tool, and this repository is content for it:

- **Trail Guide** is a command-line tool that manages the rules your agents follow in a project. It imports rules from libraries, tracks the version of each rule, and builds the guidance your agents read.
- **This library** is one collection of rules and skills you can import with it. [Fabrica](https://fabricahq.com) wrote or curated these rules from its own experience and publishes them in library releases.

It's the same relationship as a package manager and a package. You install Trail Guide once, then add this library to each project, alongside any others, such as your own team's rules.

### How are rules versioned?

Each rule has its own semantic version, such as `1.2.0`. A major version means code that followed the previous version could fail the new one. Changes reach your project in library releases, tagged `release/1`, `release/2`, and so on. Each one lists every changed rule with a summary of the change. Your project keeps the rule versions it has until you run `trailguide project update`, which shows what changed and applies it only when you confirm. See [Version your rules](https://trailguide.fabricahq.com/guides/version-rules/) and [Update rules](https://trailguide.fabricahq.com/guides/update/).

## How do I use this repo?

1. [Install Trail Guide](https://trailguide.fabricahq.com/start-here/install/) on your local computers.
2. [Set up your project](https://trailguide.fabricahq.com/start-here/set-up-project/) to use Trail Guide.
3. Add this library as a source. Within the project directory, run the command below. It selects every group and the recommended skills; delete the `--rules` lines you don't need, or the `--skills` line. Each rule follows its newest version when you update.

   ```sh
   trailguide project add source fabrica \
     --repository https://github.com/fabricahq/public-library.git \
     --rules 'practices/code-design/*' \
     --rules 'practices/concurrency/*' \
     --rules 'practices/performance/*' \
     --rules 'practices/readmes/*' \
     --rules 'practices/testing/*' \
     --rules 'techs/go/*' \
     --rules 'techs/goose/*' \
     --rules 'techs/javascript/*' \
     --rules 'techs/playwright/*' \
     --rules 'techs/react/*' \
     --rules 'techs/tanstack-query/*' \
     --rules 'techs/tanstack-router/*' \
     --rules 'techs/typescript/*' \
     --rules 'techs/zustand/*' \
     --skills recommended
   ```

   To take every group, including ones added in future library releases, pass a single wildcard instead: `--rules '*'` for everything, `--rules 'practices/*'` for all practice groups, or `--rules 'techs/*'` for all technology groups. Quote the wildcard so your shell doesn't expand it. See [Select groups from each source](https://trailguide.fabricahq.com/guides/select-rules/#select-groups-from-each-source).

   You can also leave out individual rules from a group you import. See [Exclude a rule](https://trailguide.fabricahq.com/guides/select-rules/#exclude-a-rule).

4. Download the rules and build the guidance your agent reads:

   ```sh
   trailguide project sync
   ```

5. If you haven't already, [tell your agent to read the rules](https://trailguide.fabricahq.com/start-here/set-up-project/#5-give-the-rules-to-your-agent), then commit the `.trailguide/` directory.

## FAQs

### What does a rule look like?

A rule is a Markdown file. Its YAML frontmatter gives the rule a title, says when an agent should read it, and describes why it matters. Its body states one obligation, then gives implementation guidance, incorrect and correct examples, and the evidence a reviewer should look for. For a representative example, read [Reproduce bugs with regression tests](.trailguide/rules/practices/testing/test-bug-fixes-before-fixing.md).

Every rule in this library follows the Trail Guide [rule rubric and template](https://trailguide.fabricahq.com/reference/rule-authoring/).

### Do I have to follow every rule?

No. These rules are opinions on specific technologies and practices. In some cases, you may not be using that technology, or following that practice. In some cases, you may outright disagree with the rule.

Trail Guide is designed to allow importing whatever collection of rules you want, so you can import one rule from this library, or all of them.

### What if I find a mistake in a rule?

Open a pull request that fixes it. See [How do I contribute?](#how-do-i-contribute) for how to check your change before you submit it.

These rules come from Fabrica's own real-world experience, and yours may differ. If a rule is wrong or incomplete, we welcome the fix, and everyone who uses Fabrica Public Library benefits from it.

## How do I contribute?

Open a pull request!

Be sure to follow the [Trail Guide authoring rubric](https://trailguide.fabricahq.com/reference/rule-authoring/).

When you change, add, or retire a rule, record a change note in the same pull request with `trailguide library change`. The note says how large the change is (`major`, `minor`, or `patch`) and summarizes it in one line for the people deciding whether to update. For example:

```sh
trailguide library change practices/testing/cover-boundary-cases \
  --bump minor \
  --summary 'Add an example of testing the largest allowed input.'
```

A new rule leaves out `--bump`, and a retired rule uses `--retire`. See [Change rules after the first library release](https://trailguide.fabricahq.com/guides/version-rules/#change-rules-after-the-first-library-release) for how to choose the level and record each kind of change.

Then validate the library from its root before you push:

```sh
trailguide library check
uv run .github/scripts/check-readme.py
```

The first command checks the rules and their change notes, and previews the next library release. The second checks that this README still lists every group and rule. Pull request checks run both.

Maintainers review changes in pull requests, then publish them to projects in the next library release. For the file format, see [Library format](https://trailguide.fabricahq.com/reference/library-format/).

## License and sources

The library is [MIT licensed](LICENSE.md), with copyright attributed to Fabrica Systems LLC.

Some rules adapt material from third parties, and others draw on official documentation. Adapted rules carry attribution in their metadata, and [NOTICE.md](NOTICE.md) preserves the required third-party notices. The curated pstack skills stay under pstack's own MIT license, which NOTICE.md also reproduces.
