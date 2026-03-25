from collections.abc import Iterable
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.clause import Clause
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType
from app.schemas.ai import ClauseCandidateSchema, ClauseExtractionResponseSchema
from app.services.ai import OpenAIResponsesService

logger = logging.getLogger(__name__)

CLAUSE_TAXONOMY: dict[ClauseType, tuple[str, ...]] = {
    ClauseType.indemnification: ("indemn", "hold harmless"),
    ClauseType.limitation_of_liability: ("limitation of liability", "liability cap", "cap on liability"),
    ClauseType.termination: ("termination", "terminate"),
    ClauseType.auto_renewal: ("auto renewal", "automatic renewal", "renewal term"),
    ClauseType.confidentiality: ("confidentiality", "confidential information", "non-disclosure"),
    ClauseType.assignment: ("assignment", "assign this agreement"),
    ClauseType.payment_terms: ("payment terms", "fees", "invoices", "payment due"),
    ClauseType.dispute_resolution: ("dispute resolution", "arbitration", "venue", "exclusive jurisdiction"),
    ClauseType.governing_law: ("governing law", "laws of"),
    ClauseType.ip_ownership: ("intellectual property", "ownership", "work product"),
    ClauseType.data_protection: ("data protection", "privacy", "personal data", "security measures"),
    ClauseType.warranties: ("warrant", "as is", "disclaimer"),
    ClauseType.force_majeure: ("force majeure", "acts of god"),
    ClauseType.sla: ("service level", "uptime", "availability", "response time"),
    ClauseType.audit_rights: ("audit", "inspection rights", "books and records"),
}


@dataclass(frozen=True)
class ExtractedClauseCandidate:
    clause_type: ClauseType
    title: str | None
    extracted_text: str
    confidence: float
    source_chunk_index: int
    page_start: int | None
    page_end: int | None
    source_method: str


class ClauseExtractionService:
    def __init__(self, session: Session, ai_service: OpenAIResponsesService | None = None) -> None:
        self.session = session
        self.ai_service = ai_service or OpenAIResponsesService()

    def extract_and_persist(self, document_version: DocumentVersion) -> list[Clause]:
        for clause in list(document_version.clauses):
            self.session.delete(clause)
        self.session.flush()

        extracted: list[Clause] = []
        for chunk in sorted(document_version.chunks, key=lambda value: value.chunk_index):
            heuristic = self._heuristic_extract(chunk)
            candidates = heuristic or self._ai_extract(chunk)
            for candidate in candidates:
                extracted.append(
                    Clause(
                        document_version_id=document_version.id,
                        chunk_id=chunk.id,
                        clause_type=candidate.clause_type,
                        title=candidate.title or chunk.section_title,
                        text=candidate.extracted_text,
                        normalized_text=candidate.extracted_text,
                        confidence=candidate.confidence,
                        source_method=candidate.source_method,
                        page_start=candidate.page_start,
                        page_end=candidate.page_end,
                        start_char=chunk.char_start,
                        end_char=chunk.char_end,
                    )
                )
        self.session.add_all(extracted)
        self.session.flush()
        return extracted

    def _heuristic_extract(self, chunk: DocumentChunk) -> list[ExtractedClauseCandidate]:
        haystack = f"{chunk.section_title or ''}\n{chunk.text}".lower()
        title = chunk.section_title or self._infer_title(chunk.text)
        matches: list[ExtractedClauseCandidate] = []
        for clause_type, markers in CLAUSE_TAXONOMY.items():
            if any(marker in haystack for marker in markers):
                matches.append(
                    ExtractedClauseCandidate(
                        clause_type=clause_type,
                        title=title,
                        extracted_text=chunk.text,
                        confidence=0.82,
                        source_chunk_index=chunk.chunk_index,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        source_method="heuristic",
                    )
                )
        return self._dedupe(matches)

    def _ai_extract(self, chunk: DocumentChunk) -> list[ExtractedClauseCandidate]:
        system_prompt = (
            "You classify contract chunks into a fixed clause taxonomy. "
            "Return only clauses clearly supported by the provided chunk."
        )
        user_prompt = (
            f"Chunk index: {chunk.chunk_index}\n"
            f"Section title: {chunk.section_title or 'None'}\n"
            f"Page range: {chunk.page_start or 'unknown'}-{chunk.page_end or 'unknown'}\n"
            f"Chunk text:\n{chunk.text}"
        )
        try:
            response = self.ai_service.generate_structured_output(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=ClauseExtractionResponseSchema,
                metadata={"task": "clause_extraction", "chunk_index": chunk.chunk_index},
            )
        except AppError as exc:
            if exc.code.startswith("ai_"):
                logger.warning(
                    "Clause AI extraction failed; falling back to no AI clauses for chunk",
                    extra={"chunk_index": chunk.chunk_index, "error_code": exc.code},
                )
                return []
            raise
        return [
            ExtractedClauseCandidate(
                clause_type=item.clause_type,
                title=item.title or chunk.section_title,
                extracted_text=item.extracted_text,
                confidence=item.confidence,
                source_chunk_index=item.source_chunk_index,
                page_start=item.page_start or chunk.page_start,
                page_end=item.page_end or chunk.page_end,
                source_method="ai",
            )
            for item in response.clauses
            # AI candidates are only accepted when they can be tied back to the exact
            # chunk being processed. That keeps persisted clauses auditable and avoids
            # "helpful" model paraphrases becoming source text.
            if self._candidate_matches_chunk(item, chunk)
        ]

    def _dedupe(self, candidates: Iterable[ExtractedClauseCandidate]) -> list[ExtractedClauseCandidate]:
        deduped: dict[tuple[ClauseType, str], ExtractedClauseCandidate] = {}
        for candidate in candidates:
            key = (candidate.clause_type, candidate.extracted_text)
            existing = deduped.get(key)
            if existing is None or candidate.confidence > existing.confidence:
                deduped[key] = candidate
        return list(deduped.values())

    def _infer_title(self, text: str) -> str | None:
        first_line = text.splitlines()[0].strip() if text.splitlines() else ""
        return first_line[:255] or None

    def _candidate_matches_chunk(self, candidate: ClauseCandidateSchema, chunk: DocumentChunk) -> bool:
        if candidate.source_chunk_index != chunk.chunk_index:
            logger.warning(
                "Discarding AI clause candidate with mismatched chunk index",
                extra={
                    "expected_chunk_index": chunk.chunk_index,
                    "returned_chunk_index": candidate.source_chunk_index,
                },
            )
            return False
        normalized_chunk = " ".join(chunk.text.split()).lower()
        normalized_extract = " ".join(candidate.extracted_text.split()).lower()
        # Persist only spans that are grounded in the chunk text itself; otherwise the
        # clause may be a model summary rather than an auditable extraction.
        if normalized_extract not in normalized_chunk:
            logger.warning(
                "Discarding AI clause candidate whose text is not grounded in source chunk",
                extra={"chunk_index": chunk.chunk_index},
            )
            return False
        if candidate.page_start is not None and chunk.page_start is not None and candidate.page_start < chunk.page_start:
            return False
        if candidate.page_end is not None and chunk.page_end is not None and candidate.page_end > chunk.page_end:
            return False
        return True
