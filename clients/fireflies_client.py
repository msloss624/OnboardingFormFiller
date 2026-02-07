"""
Fireflies.ai client — search transcripts by participant email domain,
retrieve full transcripts for extraction.
"""
from __future__ import annotations
import httpx
from dataclasses import dataclass, field


GQL_ENDPOINT = "https://api.fireflies.ai/graphql"


@dataclass
class TranscriptSummary:
    id: str
    title: str
    date: str
    duration: float
    participants: list[str] = field(default_factory=list)
    short_summary: str = ""


@dataclass
class FullTranscript:
    id: str
    title: str
    date: str
    speakers: list[str] = field(default_factory=list)
    sentences: list[dict] = field(default_factory=list)  # [{speaker, text, start_time}]
    summary: str = ""

    @property
    def full_text(self) -> str:
        """Combine all sentences into readable transcript text."""
        lines = []
        current_speaker = None
        current_block: list[str] = []
        for s in self.sentences:
            speaker = s.get("speaker_name", "Unknown")
            text = s.get("text", "").strip()
            if not text:
                continue
            if speaker != current_speaker:
                if current_speaker and current_block:
                    lines.append(f"**{current_speaker}**: {' '.join(current_block)}")
                current_speaker = speaker
                current_block = [text]
            else:
                current_block.append(text)
        if current_speaker and current_block:
            lines.append(f"**{current_speaker}**: {' '.join(current_block)}")
        return "\n\n".join(lines)

    @property
    def word_count(self) -> int:
        return sum(len(s.get("text", "").split()) for s in self.sentences)


class FirefliesClient:
    def __init__(self, api_key: str):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(timeout=60)

    def _query(self, query: str, variables: dict | None = None) -> dict:
        resp = self.client.post(
            GQL_ENDPOINT,
            headers=self.headers,
            json={"query": query, "variables": variables or {}},
        )
        if resp.status_code != 200:
            resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise Exception(f"Fireflies GraphQL error: {data['errors']}")
        return data.get("data", {})

    def search_by_participant(self, email_domain: str, limit: int = 20) -> list[TranscriptSummary]:
        """
        Search for transcripts where any participant's email contains the domain.
        Since Fireflies doesn't support domain-only participant search natively,
        we search by participant emails. We need at least one full email address.

        Strategy: Search recent transcripts and filter by participant domain.
        """
        query = """
        query($limit: Int) {
            transcripts(limit: $limit) {
                id
                title
                dateString: date
                duration
                participants
                summary {
                    shorthand_bullet
                }
            }
        }
        """
        data = self._query(query, {"limit": limit})
        transcripts = data.get("transcripts", [])

        results = []
        for t in transcripts:
            participants = t.get("participants") or []
            # Filter: at least one participant has the target domain
            has_domain = any(
                email_domain.lower() in (p or "").lower()
                for p in participants
            )
            if has_domain:
                results.append(TranscriptSummary(
                    id=t["id"],
                    title=t.get("title", ""),
                    date=t.get("dateString", ""),
                    duration=t.get("duration", 0),
                    participants=participants,
                    short_summary=t.get("summary", {}).get("shorthand_bullet", "") if t.get("summary") else "",
                ))
        return results

    def search_by_participant_email(self, email: str, limit: int = 20) -> list[TranscriptSummary]:
        """Search for transcripts by specific participant email."""
        query = """
        query($email: String!, $limit: Int) {
            transcripts(participant_email: $email, limit: $limit) {
                id
                title
                dateString: date
                duration
                participants
                summary {
                    shorthand_bullet
                }
            }
        }
        """
        data = self._query(query, {"email": email, "limit": limit})
        return [
            TranscriptSummary(
                id=t["id"],
                title=t.get("title", ""),
                date=t.get("dateString", ""),
                duration=t.get("duration", 0),
                participants=t.get("participants") or [],
                short_summary=t.get("summary", {}).get("shorthand_bullet", "") if t.get("summary") else "",
            )
            for t in data.get("transcripts", [])
        ]

    def get_full_transcript(self, transcript_id: str) -> FullTranscript:
        """Retrieve full transcript with all sentences."""
        query = """
        query($id: String!) {
            transcript(id: $id) {
                id
                title
                date
                speakers {
                    id
                    name
                }
                sentences {
                    speaker_name
                    text
                    start_time
                    end_time
                }
                summary {
                    shorthand_bullet
                }
            }
        }
        """
        data = self._query(query, {"id": transcript_id})
        t = data.get("transcript", {})
        speakers = [s.get("name", "") for s in (t.get("speakers") or [])]
        return FullTranscript(
            id=t.get("id", transcript_id),
            title=t.get("title", ""),
            date=t.get("date", ""),
            speakers=speakers,
            sentences=t.get("sentences") or [],
            summary=t.get("summary", {}).get("shorthand_bullet", "") if t.get("summary") else "",
        )

    def get_transcripts_for_domain(
        self, domain: str, contact_emails: list[str] | None = None, limit: int = 20
    ) -> list[FullTranscript]:
        """
        High-level: find all transcripts involving a client domain,
        then retrieve full transcripts for each.

        Tries participant email search first (more reliable),
        falls back to domain filtering.
        """
        summaries = []

        # Try each known contact email
        seen_ids: set[str] = set()
        if contact_emails:
            for email in contact_emails:
                for s in self.search_by_participant_email(email, limit=limit):
                    if s.id not in seen_ids:
                        summaries.append(s)
                        seen_ids.add(s.id)

        # Fallback: broad search filtered by domain
        if not summaries:
            summaries = self.search_by_participant(domain, limit=limit)

        # Fetch full transcripts
        full_transcripts = []
        for s in summaries:
            try:
                ft = self.get_full_transcript(s.id)
                full_transcripts.append(ft)
            except Exception:
                continue

        return full_transcripts

    def close(self):
        self.client.close()
