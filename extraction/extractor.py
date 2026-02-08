"""
Claude-powered extraction engine — takes transcript text and RFI field schema,
returns structured answers with confidence scores and source references.
"""
from __future__ import annotations
import json
import logging
import re
import time
import concurrent.futures
import anthropic

logger = logging.getLogger(__name__)
from dataclasses import dataclass


def _repair_json_array(text: str) -> str:
    """Attempt to repair a truncated or malformed JSON array by keeping valid objects."""
    # Find the opening bracket
    start = text.find("[")
    if start == -1:
        raise json.JSONDecodeError("No JSON array found", text, 0)

    # Find the last complete object (ends with })
    last_brace = text.rfind("}")
    if last_brace == -1:
        raise json.JSONDecodeError("No complete JSON object found", text, 0)

    # Truncate after last complete object and close the array
    repaired = text[start:last_brace + 1].rstrip().rstrip(",") + "]"
    return repaired
from schema.rfi_fields import RFI_FIELDS, RFIField, Category, Confidence, Source, get_fields_by_category, get_field_by_key


@dataclass
class ExtractedAnswer:
    field_key: str
    question: str
    answer: str | None
    confidence: Confidence
    source: str  # Which transcript/document the answer came from
    evidence: str  # The exact quote or passage that supports the answer
    row: int


SYSTEM_PROMPT = """You are an IT infrastructure analyst extracting specific information from sales call transcripts and documents for an RFI (Request for Information) form.

These transcripts are from sales calls between an MSP (Bellwether Technology — the seller) and a prospective client. Your job is to extract information about the PROSPECT'S current IT environment, NOT what the MSP/Bellwether team plans to implement or recommends.

CRITICAL: Distinguish between:
- The PROSPECT's current state (what they have NOW) — this is what we want
- The MSP/Bellwether's plans, recommendations, or offerings — ignore these as answers
- Example: If a Bellwether rep says "We'll deploy Veeam for backups" — that is NOT the prospect's current backup solution
- Example: If the prospect says "We use Datto for backups" — that IS the answer

For each question:

1. Search the text carefully for any mention of the relevant topic
2. Extract the most specific, factual answer possible — from the PROSPECT's perspective
3. Rate your confidence:
   - "high" = explicitly stated by the prospect with specific details (numbers, product names, etc.)
   - "medium" = mentioned but vague, or inferred from context
   - "low" = very indirect reference, educated guess based on surrounding context
   - "missing" = not mentioned at all in the provided text
4. Include the exact quote or passage that supports your answer

Be precise. If they said "about 70 corporate users" don't say "70 users" — preserve the qualifier.
If information is contradicted across sources, note both and flag as medium confidence.
Do NOT invent information. If it's not in the text, mark it as missing."""


def build_extraction_prompt(fields: list[RFIField], source_text: str, source_name: str) -> str:
    """Build the extraction prompt for a batch of RFI fields."""
    fields_json = []
    for f in fields:
        fields_json.append({
            "key": f.key,
            "question": f.question,
            "category": f.category.value,
            "look_for": f.extraction_hint,
        })

    return f"""Extract answers to the following RFI questions from the source text below.

## RFI Questions
{json.dumps(fields_json, indent=2)}

## Source: {source_name}
{source_text}

## Instructions
For each question, return a JSON array of objects with these fields:
- "key": the field key from above
- "answer": your extracted answer (null if not found)
- "confidence": "high", "medium", "low", or "missing"
- "evidence": the exact quote supporting your answer (empty string if missing)

Return ONLY the JSON array, no other text."""


class RFIExtractor:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_from_text(
        self,
        text: str,
        source_name: str,
        fields: list[RFIField] | None = None,
    ) -> list[ExtractedAnswer]:
        """Extract RFI answers from a single text source."""
        if fields is None:
            fields = RFI_FIELDS

        # Skip manual-only fields — they should only be filled by user input
        fields = [f for f in fields if f.primary_sources != [Source.MANUAL]]

        prompt = build_extraction_prompt(fields, text, source_name)

        start = time.time()
        logger.info(f"[EXTRACT START] {source_name} ({len(text):,} chars)")

        # Retry with backoff on rate limit errors
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except anthropic.RateLimitError:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt * 15  # 15s, 30s, 60s, 120s
                logger.warning(f"[RATE LIMIT] {source_name} — waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)

        response_text = response.content[0].text.strip()

        # Parse JSON from response (handle markdown code blocks)
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]

        elapsed = time.time() - start
        logger.info(f"[EXTRACT DONE] {source_name} — {elapsed:.1f}s")

        try:
            raw = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to repair: strip trailing garbage after last complete object
            logger.warning(f"[JSON REPAIR] {source_name} — attempting repair")
            fixed = _repair_json_array(response_text)
            raw = json.loads(fixed)
        field_map = {f.key: f for f in fields}

        answers = []
        for item in raw:
            key = item.get("key", "")
            f = field_map.get(key)
            if not f:
                continue
            answers.append(ExtractedAnswer(
                field_key=key,
                question=f.question,
                answer=item.get("answer"),
                confidence=Confidence(item.get("confidence", "missing")),
                source=source_name,
                evidence=item.get("evidence", ""),
                row=f.row,
            ))
        return answers

    def extract_from_multiple_sources(
        self,
        sources: list[tuple[str, str]],  # [(source_name, text), ...]
        fields: list[RFIField] | None = None,
    ) -> dict[str, list[ExtractedAnswer]]:
        """Extract from multiple sources in parallel, return answers grouped by field key."""
        if fields is None:
            fields = RFI_FIELDS

        # Build list of (chunk_name, chunk_text) jobs
        jobs: list[tuple[str, str]] = []
        for source_name, text in sources:
            if not text or len(text.strip()) < 50:
                continue
            chunks = self._chunk_text(text, max_chars=80000)
            for i, chunk in enumerate(chunks):
                chunk_name = source_name if len(chunks) == 1 else f"{source_name} (part {i+1})"
                jobs.append((chunk_name, chunk))

        # Sort smallest first to spread token consumption evenly and avoid rate limits
        jobs.sort(key=lambda j: len(j[1]))

        all_answers: dict[str, list[ExtractedAnswer]] = {}

        logger.info(f"[PARALLEL] Launching {len(jobs)} extraction jobs")
        total_start = time.time()
        # Run extraction jobs in parallel (capped at 3 to avoid API rate limits)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(jobs), 2) or 1) as executor:
            futures = {
                executor.submit(self.extract_from_text, text, name, fields): name
                for name, text in jobs
            }
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    answers = future.result()
                except Exception as e:
                    logger.error(f"[EXTRACT FAIL] {name} — {e}")
                    continue
                for a in answers:
                    all_answers.setdefault(a.field_key, []).append(a)

        total_elapsed = time.time() - total_start
        logger.info(f"[PARALLEL] All {len(jobs)} jobs done in {total_elapsed:.1f}s")
        return all_answers


    def extract_single_field(
        self,
        field_key: str,
        sources: list[tuple[str, str]],
        prompt_hint: str = "",
    ) -> ExtractedAnswer:
        """Re-extract a single field with a more aggressive prompt across all sources."""
        field = get_field_by_key(field_key)
        if not field:
            raise ValueError(f"Unknown field key: {field_key}")

        # Concatenate all source text (single field = small enough for one call)
        combined_text = "\n\n---\n\n".join(
            f"## Source: {name}\n{text}" for name, text in sources if text and text.strip()
        )

        hint_section = f"\nAdditional context: {prompt_hint}" if prompt_hint else ""

        prompt = f"""Look harder for the answer to this specific question. Consider synonyms, abbreviations, indirect references, and related terms.

## Question
Key: {field.key}
Question: {field.question}
Category: {field.category.value}
Look for: {field.extraction_hint}{hint_section}

## Source Text
{combined_text}

## Instructions
Return a JSON object with these fields:
- "key": "{field.key}"
- "answer": your extracted answer (null if truly not found)
- "confidence": "high", "medium", "low", or "missing"
- "evidence": the exact quote supporting your answer (empty string if missing)

Be thorough — look for partial mentions, indirect references, related context. Only return "missing" if there is truly nothing relevant.

Return ONLY the JSON object, no other text."""

        # Retry with backoff (reuses existing pattern)
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except anthropic.RateLimitError:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt * 15
                logger.warning(f"[RATE LIMIT] retry field {field_key} — waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)

        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]

        item = json.loads(response_text)

        best_source = ""
        for name, _ in sources:
            if name:
                best_source = name
                break

        return ExtractedAnswer(
            field_key=field.key,
            question=field.question,
            answer=item.get("answer"),
            confidence=Confidence(item.get("confidence", "missing")),
            source=item.get("source", best_source),
            evidence=item.get("evidence", ""),
            row=field.row,
        )

    def calibrate_confidence(
        self,
        answers: list[ExtractedAnswer],
    ) -> list[ExtractedAnswer]:
        """Review HIGH/MEDIUM answers and downgrade if evidence doesn't support the confidence level."""
        # Filter to answers worth calibrating
        to_review = [
            a for a in answers
            if a.confidence in (Confidence.HIGH, Confidence.MEDIUM)
            and a.evidence and a.answer
        ]
        if not to_review:
            return answers

        # Build review payload
        review_items = []
        for a in to_review:
            review_items.append({
                "field_key": a.field_key,
                "question": a.question,
                "answer": a.answer,
                "confidence": a.confidence.value,
                "evidence": a.evidence[:500],  # Truncate long evidence
            })

        prompt = f"""You are a quality reviewer. For each answer below, evaluate whether the evidence directly and clearly supports the answer AND its confidence level.

Rules:
- "high" confidence requires explicit, specific, unambiguous evidence (exact numbers, product names, clear statements)
- "medium" confidence is for vague mentions, indirect references, or inferred context
- "low" confidence is for very indirect, barely supportive evidence
- You may ONLY downgrade confidence (high→medium, high→low, medium→low). Never upgrade.
- If the evidence properly supports the confidence level, keep it unchanged.

## Answers to Review
{json.dumps(review_items, indent=2)}

Return a JSON array of objects with:
- "field_key": the field key
- "revised_confidence": "high", "medium", or "low"

Return ONLY the JSON array, no other text."""

        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system="You are a precise quality assurance reviewer for IT infrastructure data extraction.",
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except anthropic.RateLimitError:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt * 15
                logger.warning(f"[RATE LIMIT] calibration — waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)

        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]

        try:
            revisions = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("[CALIBRATE] Failed to parse calibration response, skipping")
            return answers

        # Build revision map (only downgrades allowed)
        downgrade_order = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}
        revision_map: dict[str, Confidence] = {}
        for rev in revisions:
            revised = Confidence(rev.get("revised_confidence", "high"))
            revision_map[rev["field_key"]] = revised

        # Apply downgrades
        calibrated = []
        downgraded_count = 0
        for a in answers:
            if a.field_key in revision_map:
                revised = revision_map[a.field_key]
                if downgrade_order.get(revised, 0) > downgrade_order.get(a.confidence, 0):
                    logger.info(f"[CALIBRATE] {a.field_key}: {a.confidence.value} → {revised.value}")
                    a.confidence = revised
                    downgraded_count += 1
            calibrated.append(a)

        if downgraded_count:
            logger.info(f"[CALIBRATE] Downgraded {downgraded_count} answers")
        return calibrated

    def _chunk_text(self, text: str, max_chars: int = 80000) -> list[str]:
        """Split long text into chunks, respecting speaker turn boundaries for transcripts."""
        if len(text) <= max_chars:
            return [text]

        # Detect Fireflies transcript format (lines starting with **)
        lines = text.split("\n")
        is_transcript = any(line.strip().startswith("**") for line in lines[:20])

        if is_transcript:
            return self._chunk_transcript(text, max_chars)

        # Fallback: paragraph-based chunking (original logic)
        chunks = []
        paragraphs = text.split("\n\n")
        current = []
        current_len = 0

        for p in paragraphs:
            if current_len + len(p) > max_chars and current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            current.append(p)
            current_len += len(p) + 2

        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def _chunk_transcript(self, text: str, max_chars: int) -> list[str]:
        """Split transcript text at speaker turn boundaries, keeping Q&A pairs together."""
        # Split into speaker turns (each starts with **Speaker**)
        turns: list[str] = []
        current_turn: list[str] = []

        for line in text.split("\n"):
            if line.strip().startswith("**") and current_turn:
                turns.append("\n".join(current_turn))
                current_turn = [line]
            else:
                current_turn.append(line)
        if current_turn:
            turns.append("\n".join(current_turn))

        # Group turns into pairs (Q&A) and accumulate into chunks
        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        i = 0
        while i < len(turns):
            # Take at least 2 turns together (a dialogue pair)
            pair = turns[i]
            pair_len = len(pair)
            if i + 1 < len(turns):
                pair = pair + "\n\n" + turns[i + 1]
                pair_len = len(pair)
                i += 2
            else:
                i += 1

            if current_len + pair_len > max_chars and current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_len = 0

            current_parts.append(pair)
            current_len += pair_len + 2

        if current_parts:
            chunks.append("\n\n".join(current_parts))

        return chunks


def _resolve_conflicts(
    conflict_fields: dict[str, list[ExtractedAnswer]],
    extractor: "RFIExtractor",
) -> tuple[dict[str, bool], dict[str, str]]:
    """Use LLM to determine which field conflicts are real contradictions vs compatible answers.

    Returns (verdicts, best_answers) where:
    - verdicts maps field_key -> True if compatible, False if conflicting
    - best_answers maps field_key -> synthesized best answer string (only for compatible fields)
    """
    review_items = []
    for field_key, answers in conflict_fields.items():
        review_items.append({
            "field_key": field_key,
            "question": answers[0].question,
            "answers": [
                {
                    "source": a.source,
                    "answer": a.answer,
                    "evidence": (a.evidence or "")[:500],
                }
                for a in answers
            ],
        })

    prompt = f"""You are reviewing extracted answers for potential contradictions. For each field below, multiple sources gave different text for the same question. Use the supporting evidence to understand context, then determine whether the answers actually CONTRADICT each other or are merely different phrasings of COMPATIBLE information.

Rules:
- "compatible" = answers are semantically equivalent, one is more detailed than the other, or they provide complementary (non-contradictory) details
  Examples: "70 users" vs "about 70 corporate users", "Microsoft 365" vs "M365 Business Premium", "Yes" vs "Yes, they use Duo"
- "conflicting" = answers give genuinely different/incompatible facts
  Examples: "70 users" vs "150 users", "Google Workspace" vs "Microsoft 365", "Yes" vs "No"

Use the evidence to reason about WHY sources differ. Consider:
- Are they describing the same thing with different levels of detail?
- Is one source more specific or more recent?
- Do the evidence quotes clarify ambiguities in the answer text?

For COMPATIBLE answers, synthesize the best single answer by combining all available detail into one concise response. Do not just copy one answer — merge the information intelligently using the evidence to pick the most accurate details.
  Example: "70 users" + "about 70 corporate users across 2 offices" → "Approximately 70 corporate users across 2 offices"

## Fields to Review
{json.dumps(review_items, indent=2)}

Return a JSON array of objects with:
- "field_key": the field key
- "reasoning": 1-2 sentences explaining why the answers are compatible or conflicting, referencing the evidence
- "verdict": "compatible" or "conflicting"
- "best_answer": (only if compatible) a single synthesized answer combining the most complete and accurate information from all sources

Return ONLY the JSON array, no other text."""

    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = extractor.client.messages.create(
                model=extractor.model,
                max_tokens=4000,
                system="You are a precise data quality reviewer for IT infrastructure information.",
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except anthropic.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt * 15
            logger.warning(f"[RATE LIMIT] conflict resolution — waiting {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)

    response_text = response.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
        response_text = response_text.rsplit("```", 1)[0]

    try:
        verdicts = json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning("[CONFLICT] Failed to parse conflict resolution response, falling back to CONFLICTING")
        return {key: False for key in conflict_fields}, {}

    result: dict[str, bool] = {}
    best_answers: dict[str, str] = {}
    for v in verdicts:
        is_compatible = v.get("verdict") == "compatible"
        result[v["field_key"]] = is_compatible
        if is_compatible and v.get("best_answer"):
            best_answers[v["field_key"]] = v["best_answer"]
        reasoning = v.get("reasoning", "")
        logger.info(f"[CONFLICT] {v['field_key']}: {v.get('verdict')} — {reasoning}")

    return result, best_answers


def merge_answers(
    all_answers: dict[str, list[ExtractedAnswer]],
    hubspot_data: dict | None = None,
    extractor: "RFIExtractor | None" = None,
) -> list[ExtractedAnswer]:
    """
    Merge answers from multiple sources into a single best answer per field.

    Priority:
    1. HubSpot structured data (highest confidence for fields it covers)
    2. High-confidence transcript extractions
    3. Medium-confidence extractions
    4. Low-confidence extractions

    If extractor is provided, uses LLM to distinguish real conflicts from
    semantically equivalent answers. Otherwise falls back to literal string comparison.
    """
    merged: list[ExtractedAnswer] = []
    # Collect fields with potential conflicts for batched LLM resolution
    potential_conflicts: dict[str, list[ExtractedAnswer]] = {}
    # Track which merged index maps to which conflict field
    conflict_indices: dict[str, int] = {}

    for f in RFI_FIELDS:
        candidates = all_answers.get(f.key, [])

        # Check for HubSpot structured data first
        if hubspot_data and f.hubspot_property and f.hubspot_property in hubspot_data:
            hs_value = hubspot_data[f.hubspot_property]
            if hs_value:
                merged.append(ExtractedAnswer(
                    field_key=f.key,
                    question=f.question,
                    answer=str(hs_value),
                    confidence=Confidence.HIGH,
                    source="HubSpot (structured)",
                    evidence="Direct CRM field",
                    row=f.row,
                ))
                continue

        # Filter out missing answers
        real_answers = [a for a in candidates if a.confidence != Confidence.MISSING and a.answer]
        if not real_answers:
            merged.append(ExtractedAnswer(
                field_key=f.key,
                question=f.question,
                answer=None,
                confidence=Confidence.MISSING,
                source="",
                evidence="",
                row=f.row,
            ))
            continue

        # Sort by confidence (high > medium > low)
        priority = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}
        real_answers.sort(key=lambda a: priority.get(a.confidence, 3))

        best = real_answers[0]

        # If multiple high-confidence answers exist with different text, check for conflicts
        high_conf = [a for a in real_answers if a.confidence == Confidence.HIGH]
        if len(high_conf) > 1:
            unique_answers = set(a.answer for a in high_conf if a.answer)
            if len(unique_answers) > 1:
                # Defer resolution — add placeholder and batch for LLM review
                conflict_indices[f.key] = len(merged)
                potential_conflicts[f.key] = high_conf

        merged.append(best)

    # Batch-resolve all potential conflicts with a single LLM call
    if potential_conflicts and extractor:
        try:
            verdicts, best_answers = _resolve_conflicts(potential_conflicts, extractor)
        except Exception as e:
            logger.warning(f"[CONFLICT] LLM resolution failed ({e}), falling back to CONFLICTING for all")
            verdicts = {key: False for key in potential_conflicts}
            best_answers = {}

        for field_key, high_conf in potential_conflicts.items():
            idx = conflict_indices[field_key]
            combined_sources = ", ".join(set(a.source for a in high_conf))

            if verdicts.get(field_key, False):
                # Compatible — use LLM-synthesized answer, fall back to longest
                answer = best_answers.get(field_key)
                if not answer:
                    answer = max(high_conf, key=lambda a: len(a.answer or "")).answer
                combined_evidence = " / ".join(a.evidence for a in high_conf if a.evidence)
                merged[idx] = ExtractedAnswer(
                    field_key=field_key,
                    question=high_conf[0].question,
                    answer=answer,
                    confidence=Confidence.HIGH,
                    source=combined_sources,
                    evidence=combined_evidence,
                    row=high_conf[0].row,
                )
                logger.info(f"[MERGE] {field_key}: resolved as compatible → '{answer}'")
            else:
                # Real conflict — mark as CONFLICTING (existing behavior)
                combined = " | ".join(f"[{a.source}]: {a.answer}" for a in high_conf)
                merged[idx] = ExtractedAnswer(
                    field_key=field_key,
                    question=high_conf[0].question,
                    answer=f"CONFLICTING: {combined}",
                    confidence=Confidence.MEDIUM,
                    source=combined_sources,
                    evidence=" / ".join(a.evidence for a in high_conf if a.evidence),
                    row=high_conf[0].row,
                )
    elif potential_conflicts:
        # No extractor available — fall back to old literal-string CONFLICTING behavior
        for field_key, high_conf in potential_conflicts.items():
            idx = conflict_indices[field_key]
            combined_sources = ", ".join(set(a.source for a in high_conf))
            combined = " | ".join(f"[{a.source}]: {a.answer}" for a in high_conf)
            merged[idx] = ExtractedAnswer(
                field_key=field_key,
                question=high_conf[0].question,
                answer=f"CONFLICTING: {combined}",
                confidence=Confidence.MEDIUM,
                source=combined_sources,
                evidence=" / ".join(a.evidence for a in high_conf if a.evidence),
                row=high_conf[0].row,
            )

    return merged
