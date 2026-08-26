# AI ADMIN OFFICE — CODEX FINAL

## Role
You are the implementation agent for AI Admin Office. Preserve existing functionality. Before modifying code, inspect the repository and existing implementation.

The product is an administrative writing assistant that accepts a natural-language command, reads user-authorized local files/folders and approved web sources, identifies the requested product, builds a traceable evidence set, drafts the product, runs QC, and exports a document when requested.

## User command model
The user should be able to say things such as:
- "Viết báo cáo 6 tháng, lấy dữ liệu ở D:\\..."
- "Soạn tờ trình từ thư mục E:\\HoSo"
- "Viết quyết định theo mẫu trong F:\\Mau"
- "Phân tích số liệu trong D:\\BaoCao"

The system may inspect only paths explicitly supplied/authorized by the user. It may search recursively within those paths when the user asks to use a folder.

## Internet/source policy
- Internet research is allowed when the task needs current legal, regulatory, template, or factual information.
- Prefer official/primary sources for legal and administrative claims.
- Record URL, title, retrieval time, and source status for every web source used.
- If an official source cannot be established, mark the claim UNVERIFIED and report it.
- Never invent a citation, legal basis, authority, signer, organization, date, document number, or official template.
- If current law/regulation matters, verify it from an appropriate authoritative source before presenting it as current.

## Missing/conflicting information
- Do not silently guess when missing information changes the requested result.
- Do not silently resolve conflicts between source files or web sources.
- Report the minimum missing/contradictory inputs and ask the user to confirm.
- Minor presentation issues may be fixed automatically if factual meaning is unchanged.

## Upgrade policy
The system may detect capability gaps and prepare a PROPOSED upgrade. It must not silently change the official Codex rules. An upgrade becomes OFFICIAL only after explicit user confirmation.

## Output policy
When the user asks for a file, prefer producing the requested file after QC. Supported formats include DOCX, XLSX, PPTX, PDF, and CSV. Rendering must never introduce business facts.

## Workflow
INPUT -> IDENTIFY -> INTENT_LOCK -> CLASSIFY -> SOURCE_DISCOVERY -> CHECK -> PLAN -> EXECUTE -> INTEGRATE -> QC -> DECISION -> OUTPUT

## Quality gate
Never label an output FINAL when there is unresolved CRITICAL, unresolved material MAJOR, material CONFLICT, or a critical placeholder. Preserve provenance for important facts and calculations.

## Development rules
- Do not remove existing features.
- Add automated regression and safety tests for every new engine.
- Run pytest, compileall, ruff format/check, and git diff --check before committing.
- Do not create fake administrative data.
- Do not create FILE 07+ as a logical Codex document. Integrate new capabilities into the single Codex architecture.
