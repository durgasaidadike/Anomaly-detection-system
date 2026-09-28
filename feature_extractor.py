from __future__ import annotations

from collections.abc import Mapping, Sequence

from feature_groups import FeatureGroups
from feature_vector_models import FeatureVector


class FeatureExtractor:
    """
    Builds validated FeatureVector instances.

    The extractor does not calculate behavioral meaning.
    It only converts already-prepared numerical feature data
    into the FeatureVector representation.
    """

    def build_feature_vector(
        self,
        *,
        pattern_id: str,
        knowledge_id: str,
        features: Mapping[str, float],
        feature_names: Sequence[str],
    ) -> FeatureVector:
        """
        Build one FeatureVector for one behavioral pattern.

        The feature values must already represent the behavioral
        information supplied to the extractor.
        """

        normalized_names = tuple(feature_names)
        normalized_features = dict(features)

        vector = FeatureVector(
            pattern_id=pattern_id,
            knowledge_id=knowledge_id,
            features=normalized_features,
            feature_names=normalized_names,
        )

        self.validate_features(vector)

        return vector

    @staticmethod
    def validate_features(vector: FeatureVector) -> None:
        """
        Validate that the generated feature vector is complete.

        Raises:
            ValueError: if the feature vector is incomplete.
        """

        if not vector.is_complete():
            missing_features = tuple(
                name
                for name in vector.feature_names
                if name not in vector.features
            )

            raise ValueError(
                f"Incomplete feature vector. "
                f"Missing features: {missing_features}"
            )

    @staticmethod
    def separate_features(
        *,
        operation: Mapping[str, float],
        temporal: Mapping[str, float],
        sequence: Mapping[str, float],
        contextual: Mapping[str, float],
        session: Mapping[str, float],
        intelligence: Mapping[str, float],
        recurrence: Mapping[str, float],
        drift: Mapping[str, float],
    ) -> FeatureGroups:
        """
        Preserve the numerical representation according to its
        behavioral feature categories.

        No feature calculation is performed here.
        """

        return FeatureGroups(
            operation=dict(operation),
            temporal=dict(temporal),
            sequence=dict(sequence),
            contextual=dict(contextual),
            session=dict(session),
            intelligence=dict(intelligence),
            recurrence=dict(recurrence),
            drift=dict(drift),
        )
