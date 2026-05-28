# DXM Skill

DXM is a Codex skill for bootstrapping and enforcing large-project AI collaboration rules.

When a user types `/dxm`, the skill scaffolds a project-level ruleset and tells future Codex sessions in that folder to follow it.

## What it generates

In the target project root, DXM creates or confirms these files:

- `AGENTS.md`
- `项目开发规范（AI协作）.md`
- `项目完整链路说明.md`
- `项目文件结构说明.md`
- `开发者AI开发与PR提交流程.md`

Existing hand-maintained documents are not overwritten unless the user explicitly asks for overwrite.

## Install

Use Codex's skill installer from this repo path:

```bash
install-skill-from-github.py --repo mingisrookie/dxm-skill --path skills/dxm
```

Or copy `skills/dxm` into your Codex skills directory as `dxm`.

## Use

Inside a project folder, ask Codex:

```text
/dxm
```

The skill will generate the DXM ruleset for that folder. After that, future work in the folder should obey its `AGENTS.md` and the generated long-term project documents.

## Package layout

```text
skills/dxm/
├── SKILL.md
├── agents/openai.yaml
├── assets/templates/
├── references/dxm-method.md
└── scripts/scaffold_dxm.py
```

## Safety defaults

- Non-destructive by default.
- Protects existing hand-curated project docs.
- Treats runtime data and secrets as non-reportable.
- Requires verification and documentation sync before claiming completion.

## License

MIT
