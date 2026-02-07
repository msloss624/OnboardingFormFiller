"""
Claude-powered extraction engine — takes transcript text and RFI field schema,
returns structured answers with confidence scores and source references.
"""
from __future__ import annotations
import json
import logging
import time
import concurrent.futures
import anthropic

logger = logging.getLogger(__name__)
from dataclasses import dataclass
from schema.rfi_fields import RFI_FIELDS, RFIField, Category, Confidence, Source, get_fields_by_category


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

Your job is to find answers to specific IT infrastructure questions from the provided text. For each question:

1. Search the text carefully for any mention of the relevant topic
2. Extract the most specific, factual answer possible
3. Rate your confidence:
   - "high" = explicitly stated with specific details (numbers, product names, etc.)
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

        prompt = build_extraction_prompt(fields, text, source_name)

        start = time.time()
        logger.info(f"[EXTRACT START] {source_name} ({len(text):,} chars)")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()

        # Parse JSON from response (handle markdown code blocks)
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]

        elapsed = time.time() - start
        logger.info(f"[EXTRACT DONE] {source_name} — {elapsed:.1f}s")

        raw = json.loads(response_text)
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

        all_answers: dict[str, list[ExtractedAnswer]] = {}

        logger.info(f"[PARALLEL] Launching {len(jobs)} extraction jobs")
        total_start = time.time()
        # Run all extraction jobs in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs) or 1) as executor:
            futures = {
                executor.submit(self.extract_from_text, text, name, fields): name
                for name, text in jobs
            }
            for future in concurrent.futures.as_completed(futures):
                answers = future.result()
                for a in answers:
                    all_answers.setdefault(a.field_key, []).append(a)

        total_elapsed = time.time() - total_start
        logger.info(f"[PARALLEL] All {len(jobs)} jobs done in {total_elapsed:.1f}s")
        return all_answers


    def _chunk_text(self, text: str, max_chars: int = 80000) -> list[str]:
        """Split long text into chunks at paragraph boundaries."""
        if len(text) <= max_chars:
            return [text]

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


def merge_answers(
    all_answers: dict[str, list[ExtractedAnswer]],
    hubspot_data: dict | None = None,
) -> list[ExtractedAnswer]:
    """
    Merge answers from multiple sources into a single best answer per field.

    Priority:
    1. HubSpot structured data (highest confidence for fields it covers)
    2. High-confidence transcript extractions
    3. Medium-confidence extractions
    4. Low-confidence extractions
    """
    field_map = {f.key: f for f in RFI_FIELDS}
    merged: list[ExtractedAnswer] = []

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

        # If multiple high-confidence answers exist, combine them
        high_conf = [a for a in real_answers if a.confidence == Confidence.HIGH]
        if len(high_conf) > 1:
            combined_sources = ", ".join(set(a.source for a in high_conf))
            # Check for contradictions
            unique_answers = set(a.answer for a in high_conf if a.answer)
            if len(unique_answers) > 1:
                combined = " | ".join(f"[{a.source}]: {a.answer}" for a in high_conf)
                best = ExtractedAnswer(
                    field_key=f.key,
                    question=f.question,
                    answer=f"CONFLICTING: {combined}",
                    confidence=Confidence.MEDIUM,
                    source=combined_sources,
                    evidence=" / ".join(a.evidence for a in high_conf if a.evidence),
                    row=f.row,
                )

        merged.append(best)

    return merged
