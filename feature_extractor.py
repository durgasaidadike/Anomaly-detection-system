from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from feature_groups import FeatureGroups
from feature_validator import FeatureValidator
from feature_vector_models import FeatureVector
from normalization_engine import NormalizationEngine


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
    def validate_features(
        vector: FeatureVector,
    ) -> None:
        """
        Validate the structural and numerical integrity of a
        generated feature vector.
        """

        FeatureValidator.validate(
            pattern_id=vector.pattern_id,
            knowledge_id=vector.knowledge_id,
            features=vector.features,
            feature_names=vector.feature_names,
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

    @staticmethod
    def construct_features(
        groups: FeatureGroups,
    ) -> tuple[dict[str, float], tuple[str, ...]]:
        """
        Construct a deterministic flat feature representation from
        separated behavioral feature groups.

        No numerical transformation or feature calculation is
        performed here. Existing numerical values are only organized
        into a stable feature namespace and ordering.
        """

        constructed_features: dict[str, float] = {}
        feature_names: list[str] = []

        for group_name, group_features in groups.as_groups().items():
            for feature_name, value in group_features.items():
                qualified_name = f"{group_name}.{feature_name}"

                constructed_features[qualified_name] = value
                feature_names.append(qualified_name)

        return constructed_features, tuple(feature_names)

    @staticmethod
    def normalize_features(
        features: Mapping[str, float],
        normalizers: Mapping[str, Callable[[float], float]],
    ) -> dict[str, float]:
        """
        Normalize an already-constructed numerical feature
        representation using explicitly supplied rules.

        FeatureExtractor orchestrates the transformation but
        does not define feature-specific normalization policy.
        """

        return NormalizationEngine.normalize_features(
            features,
            normalizers,
        )

    @staticmethod
    def build_normalized_feature_vector(
        *,
        pattern_id: str,
        knowledge_id: str,
        features: Mapping[str, float],
        feature_names: Sequence[str],
        normalizers: Mapping[str, Callable[[float], float]],
    ) -> FeatureVector:
        """
        Build one validated FeatureVector after numerical normalization.

        Processing order:

            source numerical features
                    ↓
                normalization
                    ↓
              feature validation
                    ↓
                FeatureVector

        Normalization rules are explicitly supplied by the caller.
        """

        normalized_features = NormalizationEngine.normalize_features(
            features,
            normalizers,
        )

        return FeatureExtractor().build_feature_vector(
            pattern_id=pattern_id,
            knowledge_id=knowledge_id,
            features=normalized_features,
            feature_names=feature_names,
        )
