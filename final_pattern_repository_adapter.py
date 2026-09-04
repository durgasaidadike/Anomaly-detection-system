from __future__ import annotations

from typing import Optional

from candidate_pattern_models import CandidatePattern
from final_pattern_factory import FinalPatternFactory
from final_pattern_repository import FinalPatternRepository


class FinalPatternRepositoryAdapter:
    """
    Bridges finalized CandidatePattern instances into the
    immutable FinalPattern + FinalPatternRepository pipeline.

    The Candidate Pattern Manager remains responsible only for
    Candidate Pattern lifecycle management.
    """

    def __init__(
        self,
        repository: Optional[
            FinalPatternRepository
        ] = None,
        factory: Optional[
            FinalPatternFactory
        ] = None,
    ) -> None:
        self._repository = (
            repository
            or FinalPatternRepository()
        )

        self._factory = (
            factory
            or FinalPatternFactory()
        )

    def store(
        self,
        pattern: CandidatePattern,
    ) -> bool:
        """
        Convert a completed CandidatePattern into an immutable
        FinalPattern and store it in the repository.
        """

        final_pattern = self._factory.create(
            pattern
        )

        if final_pattern is None:
            return False

        return self._repository.store(
            final_pattern
        )

    def get_repository(
        self,
    ) -> FinalPatternRepository:
        """
        Return the underlying FinalPatternRepository.

        This accessor allows higher-level integration code to inspect
        repository state without making the Candidate Pattern Manager
        aware of repository internals.
        """

        return self._repository
