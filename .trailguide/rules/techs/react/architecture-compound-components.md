---
title: "Build complex components from composable parts"
whenToRead: "Before planning, writing, changing, or reviewing a React component with several optional or rearrangeable parts, such as a composer, card, or dialog configured through show flags or render props."
impact: "MEDIUM"
impactDescription: "Monolithic components configured through flags and render props grow a prop for every new arrangement and are hard for callers to read."
tags: "react, composition, compound-components, children"
attribution:
  - url: https://github.com/vercel-labs/agent-skills/tree/4ec6f84b61cd3c931046c3e6e398f3ae7de372f7/skills/composition-patterns/rules
    description: "Adapted from two Vercel Agent Skills rules (architecture-compound-components and patterns-children-over-render-props): merged with the children-over-render-props rule, restructured to the rule template, and recalibrated impact."
---

## Build complex components from composable parts

When callers need different arrangements of a component's parts, expose compound components they compose as children, sharing state through context.
Keep a complete component for a repeated standard arrangement so ordinary callers do not have to assemble it.
Use render props only when the component must pass data back to the caller's content.

### Implementation

- Expose parts when callers need structural variation, such as a custom header or a different placement of actions.
  Export those parts together, such as `Composer.Frame`, `Composer.Input`, and `Composer.Submit`.
- Provide a complete component for a repeated standard arrangement, composing the same parts internally.
  It should own meaningful defaults and coordination rather than merely rename another component.
  A cohesive component with no structural customization needs no compound API.
- Share state and actions among the parts through a context provided by the root or a provider component, instead of threading props through every part.
- Replace collections of `showX` flags and `renderX` props that encode different static arrangements with children.
  Behavioral props such as `disabled` do not by themselves call for a compound API.
- Keep a render prop, such as `renderItem`, when the component supplies data to each piece of caller content.

### Rationale

A component that configures many arrangements through flags needs another prop for each new structural choice.
Callers then configure structure indirectly through flags and callbacks.
With composable parts, callers write custom structure directly.
A complete component owns the repeated standard arrangement, so changing that arrangement does not require coordinated edits across ordinary callers.

### Examples

#### Application: Optional parts

**Incorrect (counterexample):**

```tsx
<Composer
  showAttachments
  showFormatting={false}
  renderHeader={() => <CustomHeader />}
  renderActions={() => <SubmitButton />}
/>
```

**Correct:**

```tsx
<Composer.Provider state={state} actions={actions}>
  <Composer.Frame>
    <CustomHeader />
    <Composer.Input />
    <Composer.Footer>
      <Composer.Attachments />
      <Composer.Submit />
    </Composer.Footer>
  </Composer.Frame>
</Composer.Provider>
```

Callers that need this custom arrangement see and control which parts appear and in what order.

#### Application: A repeated standard arrangement

**Incorrect (counterexample):**

Every ordinary message form repeats the provider, input, attachments, footer, and submit composition above and initializes the same local state.
A change to the standard arrangement requires editing every caller.

**Correct:**

```tsx
<MessageComposer onSubmit={sendMessage} />
```

`MessageComposer` owns the standard arrangement and local state, using the same compound parts internally.
Callers supply the submission behavior they own.
A caller that needs a custom arrangement can still compose the parts directly; the standard component does not accumulate a mode flag for each variation.

#### Application: Content that needs data from the component

**Correct:**

```tsx
<List items={items} renderItem={(item) => <ItemRow item={item} />} />
```

The list supplies each item, so a render prop is the right tool.

### Validation

Check components with several `showX` or `renderX` props for static structure; when those props encode different arrangements, callers should be able to compose the parts.
Inspect ordinary call sites too: repeated setup and standard arrangements should have a complete component that owns them.

A render prop that receives data from the component, a behavioral flag, or a cohesive component without structural customization is not a violation.
