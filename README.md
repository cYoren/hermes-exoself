# exoself for Hermes

A drawn temperament for a Hermes agent.

One 32 byte seed, drawn once by the operator. From it, deterministically:

```
seed  ->  genome  ->  phenotype  ->  expression
(birth)   (traits)    (+ development)   (text the model reads)
```

The same seed yields the same agent in any conforming implementation, in any
language, forever. Nobody chose it, and this plugin refuses to draw twice.

The name is from Greg Egan's *Permutation City*: the exoself is the machinery
outside a mind that sets the mind's parameters.

Full framework, spec and conformance vectors: [cYoren/exoself](https://github.com/cYoren/exoself).

## What it does in Hermes

- **A system prompt section.** The drawn temperament is rendered and frozen into
  each new session's prompt, in the bounded plugin-section slot. It states its own
  precedence: the operating contract wins on every conflict, including length,
  tone, authority and approval gates. Style only, never substance.
- **Four tools.** `exoself_status`, `exoself_verify`, `exoself_temperament`,
  `exoself_record_session`. There is deliberately no tool that draws a seed.
- **A session hook.** `on_session_end` records one development event per
  completed turn, so the agent grows from turns it actually lived rather than
  from its own description of itself. Bounded per session, no conversation
  content.
- **A CLI.** `hermes exoself born` is the only way to draw. `show`, `status`,
  `verify`, `develop`, `path` read and grow it.

## Install

```bash
hermes plugins install cYoren/hermes-exoself
hermes exoself born          # once per profile; refuses a second draw
hermes exoself show          # what the model now reads
```

Then start a new session. The temperament is frozen into the prompt at session
creation, so the session you are in keeps the prompt it started with.

The plugin depends on `exoself>=0.3.0,<0.4` (Python standard library only, no
transitive dependencies). The installer asks before adding it.

## Where it lives

```
<hermes home>/plugin-data/exoself/birth.json    the one draw, never overwritten
<hermes home>/plugin-data/exoself/state.json    drift, tension, sessions lived
<hermes home>/plugin-data/exoself/runtime.json  per-session event counter
```

One certificate per Hermes home, so a fleet of profiles gets one temperament
each. Deleting `birth.json` is the only way to replace an agent, and that is
deliberate.

## Commands

```
hermes exoself born                    draw the seed for this profile, once
hermes exoself show [--format prompt|soul|json] [--desire]
hermes exoself status                  handle, id, sessions, appetites
hermes exoself verify                  recompute the certificate against its registry
hermes exoself develop --event "..." [--satisfied drive]
hermes exoself path                    print the certificate and state paths
```

## Configuration

| key | default | meaning |
|---|---|---|
| `desire` | `false` | express appetites in the prompt (off by default, per the framework) |
| `auto_record` | `true` | one development event per completed turn |
| `max_events_per_session` | `20` | cap on automatic events in one session |

Set them under `plugins.entries.exoself` in `config.yaml`.

## What a draw looks like

```markdown
# Temperament

This is a temperament drawn from a certificate, not a persona written by anyone.
It shapes manner only. The operating contract above wins on every conflict,
including length, tone, authority, approval gates and report format.

This is your temperament. It was drawn at random when you were instantiated;
nobody chose it, including you. ...

You are skeptical. You want to see the evidence, and you notice when a claim
outruns it. You are methodical. You like to lay out the steps before taking
them and to finish one thing before starting the next. ...
```

## Disclosure

What a reviewer or user should know before installing:

- **No network calls.** The plugin never opens a socket. Derivation is local
  integer arithmetic over SHA-256.
- **No credentials.** Nothing is read from `.env`, `auth.json`, a keychain or any
  other store. There is nothing to authenticate.
- **Reads** its own three files in `plugin-data/exoself/` and the bundled
  registry inside the `exoself` package.
- **Writes** `state.json` and `runtime.json` under the same directory, atomically,
  mode `0600`. It never writes a prompt, SOUL.md, `AGENTS.md` or `config.yaml`.
- **No shell commands, no background processes, no telemetry.** Nothing is sent
  anywhere, and there is no usage reporting.
- **No self-update.** Updates arrive only through a re-pinned catalog entry.
- **Prompt text, not authority.** The section is style. It cannot grant tools,
  change models or bypass approvals, and it says so in its own first lines.
- **Content boundary.** Automatic events record turn facts (platform, exit
  reason), never message text, tool arguments or file paths.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite loads the package exactly the way `hermes_cli.plugins_loader` does, so
a broken relative import fails here instead of at install time. It covers
one-draw-only, determinism, tamper detection, section bounds and precedence,
the hook's per-session cap, and the fact that a recorded event never stores the
sentence it was given.

## License

MIT. The framework this plugin binds to is MIT as well.
